# @version 0.3.0
# @notice A manager contract for the FarmingRewards contract.
# @license MIT
from vyper.interfaces import ERC20


interface AaveIncentivesController:
    def getDistributionEnd() -> uint256: view
    def setDistributionEnd(deistributionEnd: uint256): nonpayable
    def configureAssets(assets: address[1], emissionsPerSecond: uint256[1]): nonpayable
    def setDistributionPeriod(start: uint256, end: uint256): nonpayable
event OwnershipTransferred: 
    previous_owner: indexed(address)
    new_owner: indexed(address)


event RewardsContractSet:
    rewards_contract: indexed(address)


event ERC20TokenRecovered:
    token: indexed(address)
    amount: uint256
    recipient: indexed(address)


owner: public(address)
rewards_contract: public(address)
rewards_initializer: public(address)
rewards_duration: public(uint256)
ldo_token: constant(address) = 0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32
staking_token: public(address)

@external
def __init__(_rewards_initializer: address):
    assert _rewards_initializer != ZERO_ADDRESS, "rewards initializer: zero address"

    self.owner = msg.sender
    log OwnershipTransferred(ZERO_ADDRESS, msg.sender)

    self.rewards_initializer = _rewards_initializer

@external
def set_asset(asset: address):
    assert msg.sender == self.owner, "not permitted"
    self.staking_token = asset

@external
def transfer_ownership(_to: address):
    """
    @notice
        Changes the contract owner.
        Can only be called by the current owner.
    """
    old_owner: address = self.owner
    assert msg.sender == old_owner, "not permitted"
    self.owner = _to

    log OwnershipTransferred(old_owner, _to)

@view
@internal
def _period_finish() -> uint256:
    return AaveIncentivesController(self.rewards_contract).getDistributionEnd()

@view
@external
def period_finish() -> uint256:
    return self._period_finish()

@view
@internal
def _is_rewards_period_finished() -> bool:
    return block.timestamp >= self._period_finish()


@view
@external
def is_rewards_period_finished() -> bool:
    """
    @notice Whether the current rewards period has finished.
    """
    return block.timestamp > AaveIncentivesController(self.rewards_contract).getDistributionEnd()

@external
def start_next_rewards_period():
    """
    @notice
        Starts the next rewards via calling `FarmingRewards.notifyRewardAmount()`
        and transferring `ldo_token.balanceOf(self)` tokens to `FarmingRewards`.
        The `FarmingRewards` contract handles all the rest on its own.
        The current rewards period must be finished by this time.
        First period could be started only by `self.rewards_initializer`
    """
    rewards_contract: address = self.rewards_contract

    assert self._period_finish() > 0 or self.rewards_initializer == msg.sender, "manager: not initialized"
    
    amount: uint256 = ERC20(ldo_token).balanceOf(self)

    assert amount != 0, "manager: rewards disabled"
    assert self._is_rewards_period_finished(), "manager: rewards period not finished"

    assert ERC20(ldo_token).transfer(rewards_contract, amount), "manager: unable to transfer reward tokens"

    AaveIncentivesController(rewards_contract).setDistributionPeriod(block.timestamp, block.timestamp + self.rewards_duration)
    emission_per_second: uint256 = amount / self.rewards_duration
    AaveIncentivesController(rewards_contract).configureAssets([self.staking_token], [emission_per_second])


@external
def set_rewards_contract(rewards_contract: address):
    assert msg.sender == self.owner, "not permited"
    self.rewards_contract = rewards_contract
    log RewardsContractSet(rewards_contract)

@external
def set_rewards_period_duration(_duration: uint256):
    """
    @notice
        Updates period duration.  Can only be called by the owner.
    """
    assert msg.sender == self.owner, "manager: not permitted"

    self.rewards_duration = _duration
    # FarmingRewards(self.rewards_contract).setDuration(GIFT_INDEX, _duration)


@external
def recover_erc20(_token: address, _amount: uint256, _recipient: address = msg.sender):
    """
    @notice
        Transfers the given _amount of the given ERC20 token from self
        to the recipient. Can only be called by the owner.
    """
    assert msg.sender == self.owner, "not permitted"

    if _amount != 0:
        assert ERC20(_token).transfer(_recipient, _amount), "token transfer failed"
        log ERC20TokenRecovered(_token, _amount, _recipient)
    