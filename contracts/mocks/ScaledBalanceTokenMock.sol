// SPDX-License-Identifier: agpl-3.0
pragma solidity 0.7.5;

import {IScaledBalanceToken} from '../interfaces/IScaledBalanceToken.sol';

contract ScaledBalanceTokenMock is IScaledBalanceToken {
    uint256 public totalSupply;
    mapping(address => uint256) balances;
  /**
   * @dev Returns the scaled balance of the user. The scaled balance is the sum of all the
   * updated stored balance divided by the reserve's liquidity index at the moment of the update
   * @param user The user whose balance is calculated
   * @return The scaled balance of the user
   **/
  function scaledBalanceOf(address user) external view override returns (uint256) {
      return balances[user];
  }

  /**
   * @dev Returns the scaled balance of the user and the scaled total supply.
   * @param user The address of the user
   * @return The scaled balance of the user
   * @return The scaled balance and the scaled total supply
   **/
  function getScaledUserBalanceAndSupply(address user) external view override returns (uint256, uint256) {
      return (balances[user], totalSupply);
  }

  /**
   * @dev Returns the scaled total supply of the token. Represents sum(debt/index)
   * @return The scaled total supply
   **/
  function scaledTotalSupply() external view override returns (uint256) {
      return totalSupply;
  }

  function mint(address user, uint256 amount) external {
      balances[user] += amount;
      totalSupply += amount;
  }

  function burn(address user, uint256 amount) external {
      balances[user] -= amount;
      totalSupply += amount;
  }
}