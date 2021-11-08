// SPDX-License-Identifier: agpl-3.0
pragma solidity 0.8.9;

import { IERC20 } from "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/token/ERC20/utils/SafeERC20.sol";
import { AccessControl } from "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

struct Reward {
  uint256 upcomingReward;
  uint256 paidReward;
  uint256 rewardPerTokenPaid;
  uint256 updatedAt;
}

struct RewardsState {
  uint256 endDate;
  uint256 updatedAt;
  uint256 rewardPerToken;
  uint256 rewardPerSecond;
  mapping(address => Reward) rewards;
}

library RewardsUtils {
  uint256 constant PRECISION = 1e18;

  function updateRewardPeriod(
    RewardsState storage config,
    uint256 endDate,
    uint256 rewardPerSecond,
    uint256 totalStaked
  ) internal {
    config.rewardPerToken =
      config.rewardPerToken +
      _unaccountedRewardPerToken(config, totalStaked);
    config.endDate = endDate;
    config.updatedAt = block.timestamp;
    config.rewardPerSecond = rewardPerSecond;
  }

  function earned(RewardsState storage config, uint256 totalStaked, address staker, uint256 staked)
    internal
    view
    returns (uint256)
  {
    Reward storage stakerReward = config.rewards[staker];
    return stakerReward.upcomingReward + staked * (
        config.rewardPerToken + _unaccountedRewardPerToken(config, totalStaked) - stakerReward.rewardPerTokenPaid
      ) / PRECISION;
  }

  function payReward(RewardsState storage config, uint256 totalStaked, address staker, uint256 staked)
    internal
    returns (uint256)
  {
    updateReward(config, totalStaked, staker, staked);
    uint256 earnedReward = earned(config, totalStaked, staker, staked);
    config.rewards[staker].upcomingReward = 0;
    config.rewards[staker].paidReward += earnedReward;
    return earnedReward;
  }

  function updateReward(RewardsState storage config, uint256 totalStaked, address staker, uint256 staked)
    internal
  {
    uint256 updatedAt = _blockTimestampOrEndDate(config);
    config.rewardPerToken =
      config.rewardPerToken +
      _unaccountedRewardPerToken(config, totalStaked);
    config.updatedAt = updatedAt;
    config.rewards[staker].upcomingReward = earned(config, totalStaked, staker, staked);
    config.rewards[staker].rewardPerTokenPaid = config.rewardPerToken;
    config.rewards[staker].updatedAt = updatedAt;
  }

  function _unaccountedRewardPerToken(
    RewardsState storage config,
    uint256 totalStaked
  ) private view returns (uint256) {
    if (totalStaked == 0) {
      return 0;
    }
    uint256 blockTimesmapOrEndDate = _blockTimestampOrEndDate(config);
    uint256 updatedAt = config.updatedAt;
    uint256 timeDelta = blockTimesmapOrEndDate - updatedAt;
    return (PRECISION * timeDelta * config.rewardPerSecond) / totalStaked;
  }

  function _blockTimestampOrEndDate(RewardsState storage config)
    private
    view
    returns (uint256)
  {
    uint256 endDate = config.endDate;
    return endDate > block.timestamp ? block.timestamp : endDate;
  }
}

interface IScaledBalanceToken {
  function scaledTotalSupply() external view returns (uint256);
  function getScaledUserBalanceAndSupply(address user) external view returns (uint256, uint256);
}


contract IncentivesController is AccessControl {
  using RewardsUtils for RewardsState;
  using SafeERC20 for IERC20;

  bytes32 public constant EMISSION_MANAGER_ROLE = keccak256("INCENTIVES_CONTROLLER_EMISSION_MANAGER");
  bytes32 public constant ASSET_ROLE = keccak256("INCENTIVES_CONTROLLER_ASSET");

  RewardsState rewardsState;
  IERC20 rewardToken;
  uint256 rewardsDuration;
  IScaledBalanceToken stakingToken;
  

  constructor(address _rewardToken, address _emissionManager) {
    rewardToken = IERC20(_rewardToken);
    _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    _setupRole(EMISSION_MANAGER_ROLE, _emissionManager);
  }

  function setStakingToken(address _stakingToken) external {
    address stakingTokenAddress = address(stakingToken);
    if (hasRole(ASSET_ROLE, stakingTokenAddress)) {
      revokeRole(ASSET_ROLE, stakingTokenAddress);
    }
    grantRole(ASSET_ROLE, _stakingToken);
    stakingToken = IScaledBalanceToken(_stakingToken);
  }

  function periodFinish() external view returns (uint256) {
    return rewardsState.endDate;
  }

  function startRewardPeriod(uint256 rewardAmount, address rewardHolder)
    external onlyRole(EMISSION_MANAGER_ROLE)
  {
    require(rewardsState.endDate == 0 || rewardsState.endDate <= block.timestamp, 'REWARD_PERIOD_NOT_FINISHED');
    rewardToken.safeTransferFrom(rewardHolder, address(this), rewardAmount);
    uint256 endDate = block.timestamp + rewardsDuration;
    uint256 rewardPerSecond = rewardAmount / rewardsDuration;
    uint256 scaledTotalSupply = stakingToken.scaledTotalSupply();
    rewardsState.updateRewardPeriod(endDate, rewardPerSecond, scaledTotalSupply);
  }

  function earned(address staker) external view returns (uint256) {
    (uint256 staked, uint256 totalStaked) = stakingToken.getScaledUserBalanceAndSupply(staker);
    return rewardsState.earned(totalStaked, staker, staked);
  }

  function handleAction(
      address user,
      uint256 totalSupply,
      uint256 userBalance
  ) external onlyRole(ASSET_ROLE) {
      rewardsState.updateReward(totalSupply, user, userBalance);
  }

  function setRewardsDuration(uint256 newRewardsDuration) external onlyRole(DEFAULT_ADMIN_ROLE) {
    rewardsDuration = newRewardsDuration;
  }

  function claimReward() external {
    (uint256 stakedByUser, uint256 totalStaked) = stakingToken.getScaledUserBalanceAndSupply(msg.sender);
    uint256 earnedRewards = rewardsState.payReward(totalStaked, msg.sender, stakedByUser);
    if (earnedRewards > 0) {
      rewardToken.safeTransfer(msg.sender, earnedRewards);
    }
  }
}
