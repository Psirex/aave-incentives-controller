from brownie import ZERO_ADDRESS, Wei
from deployment.deploy import deploy_implementation
from brownie.network import chain, history
from conftest import load_dependency_contract


def is_almost_equal(a, b, epsilon=100):
    return abs(a - b) < epsilon

# 1. Add new reserve to AAVE lending pool
# 2. Call initializeDebtToken on AStETH token proxy
# 3. Start new reward period
# 4. Depositor1 send StETH to the reserve
# 5. Depositor2 send StETH to the reserve
# 6. Wait half of the reward period
# 7. Validate that both depositors received expected reward
# 8. Wait till the end of the reward period
# 9. Validate that both depositors received expected reward
# 10. Depositor1 claims earned reward
# 11. Start next reward period
# 12. Depositor2 makes another deposit
# 13. Wait half of the reward period
# 14. Validate that both depositors received expected reward
# 15. Depositor1 extract StETH from reserve
# 16. Wait till the end of the reward period
# 17. Validate that depositors have expected reward
# 18. Skip one reward period
# 19. Start new reward period
# 20. Depositor3 deposit StETH into the reserve
# 21. Wait till the end of reward period
# 22. Validate that depositors received expected amount of rewards


def test_happy_path(Contract, owner, admin, incentives_controller,
                    rewards_manager, rewards_initializer, agent, ldo, depositors,
                    lending_pool_configurator, pool_admin, asteth_impl,
                    variable_debt_steth_impl, stable_debt_steth_impl, lending_pool, steth):

    lending_pool_configurator.initReserve(
        asteth_impl,
        stable_debt_steth_impl,
        variable_debt_steth_impl,
        18,
        '0x4ce076b9dD956196b814e54E1714338F18fde3F4',  # interest rate strategy WETH
        {'from': pool_admin})

    # call initializeDebtToken on AStETH token proxy
    reserve_data = lending_pool.getReserveData(
        '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')
    [asteth, stable_debt_steth_address,
        variable_debt_steth_address] = reserve_data[7:10]

    # get asteth with proxy
    AStETH = load_dependency_contract('AStETH')
    asteth = Contract.from_abi('AStETH', asteth, AStETH.abi)

    # initialize asteth reference to debt token
    asteth.initializeDebtToken({'from': owner})

    # get variable debt steth with proxy
    VariableDebtStETH = load_dependency_contract('VariableDebtStETH')
    variable_debt_steth = Contract.from_abi(
        'VariableDebtStETH', variable_debt_steth_address, VariableDebtStETH.abi)

    # get stable debt steth with proxy
    StableDebtStETH = load_dependency_contract('StableDebtStETH')
    stable_debt_steth = Contract.from_abi(
        'StableDebtStETH', stable_debt_steth_address, StableDebtStETH.abi)

    rewards_manager.set_asset(asteth, {'from': owner})
    ldo.transfer(rewards_manager, '1000 ether', {'from': agent})
    assert ldo.balanceOf(rewards_manager) == '1000 ether'
    rewards_manager.set_rewards_contract(
        incentives_controller, {'from': owner})
    rewards_manager.set_rewards_period_duration(
        30 * 24 * 60 * 60, {'from': owner})
    tx = rewards_manager.start_next_rewards_period(
        {'from': rewards_initializer})

    # mint some amount of tokens to user
    [depositor1, depositor2, depositor3] = depositors

    # depositor1 send ether into the pool
    steth.approve(lending_pool, '1000 ether', {'from': depositor1})
    deposit1 = Wei('1 ether')
    lending_pool.deposit(steth, deposit1, depositor1,
                         0, {'from': depositor1})
    assert is_almost_equal(asteth.balanceOf(depositor1), deposit1)
    assert is_almost_equal(steth.balanceOf(depositor1), 0)

    # depositor2 send ether into the pool
    steth.approve(lending_pool, '1000 ether', {'from': depositor2})
    deposit2 = Wei('0.5 ether')
    tx = lending_pool.deposit(steth, deposit2, depositor2,
                              0, {'from': depositor2})

    assert is_almost_equal(steth.balanceOf(depositor2), Wei('0.5 ether'))
    assert is_almost_equal(asteth.balanceOf(depositor2), deposit2)

    # wait for half of the reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()

    # validate that both depositors earned rewards according to their parts in reserve
    depositor1_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor1)
    depositor1_expected_reward = int(0.5 *
                                     asteth.balanceOf(depositor1) * Wei('1000 ether') / asteth.totalSupply())
    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor2)
    depositor2_expected_reward = int(0.5 *
                                     asteth.balanceOf(depositor2) * Wei('1000 ether') / asteth.totalSupply())

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    print('Depositor 1:', depositor1_actual_reward)
    print('Depositor 2', depositor2_actual_reward)

    # wait till the end of the reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()
    assert rewards_manager.is_rewards_period_finished()

    # validate that both depositors earned rewards according to their parts in reserve
    depositor1_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor1)
    depositor1_expected_reward = int(
        asteth.balanceOf(depositor1) * Wei('1000 ether') / asteth.totalSupply())
    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor2)
    depositor2_expected_reward = int(
        asteth.balanceOf(depositor2) * Wei('1000 ether') / asteth.totalSupply())

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    print('Depositor 1:', depositor1_actual_reward)
    print('Depositor 2', depositor2_actual_reward)

    # depositor1 claims rewards
    assert ldo.balanceOf(depositor1) == 0
    incentives_controller.claimRewards(
        [asteth], depositor1_actual_reward, depositor1, {'from': depositor1})
    assert ldo.balanceOf(depositor1) == depositor1_actual_reward
    assert incentives_controller.getRewardsBalance(
        [asteth.address], depositor1) == 0

    # start next rewards period
    ldo.transfer(rewards_manager, '1000 ether', {'from': agent})
    assert ldo.balanceOf(rewards_manager) == Wei('1000 ether')
    rewards_manager.start_next_rewards_period(
        {'from': rewards_initializer})
    assert ldo.balanceOf(rewards_manager) == 0

    # depositor2 makes another deposit
    print('Depositor2 unclaimed rewards before deposit:',
          incentives_controller.getUserUnclaimedRewards(depositor2))
    print('Depositor2 reward before deposit:', incentives_controller.getRewardsBalance(
        [asteth.address], depositor2))
    print()
    deposit2 = Wei('0.5 ether')
    tx = lending_pool.deposit(steth, deposit2, depositor2,
                              0, {'from': depositor2})
    print('Depositor2 reward after deposit:', incentives_controller.getRewardsBalance(
        [asteth.address], depositor2))
    print('Depositor2 unclaimed rewards after deposit:',
          incentives_controller.getUserUnclaimedRewards(depositor2))
    print()
    depositor2_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor2)
    print('depositor2_actual_reward:', depositor2_actual_reward)

    # wait half of the period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()

    # validate that both depositors earned rewards according to their parts in reserve
    depositor1_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor1)
    depositor1_expected_reward = int(0.5 *
                                     asteth.balanceOf(depositor1) * Wei('1000 ether') / asteth.totalSupply())

    print('Depositor 1 before withdraw:', depositor1_actual_reward)

    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_expected_reward = depositor2_actual_reward + int(0.5 *
                                                                asteth.balanceOf(depositor2) * Wei('1000 ether') / asteth.totalSupply())
    depositor2_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor2)

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    # depositor1 extract asteth from reserve
    lending_pool.withdraw(steth,  2**256 - 1,
                          depositor1, {'from': depositor1})

    assert is_almost_equal(asteth.balanceOf(depositor1), 0)
    assert is_almost_equal(steth.balanceOf(depositor1), 10 ** 18)

    # wait till the end of reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()
    assert rewards_manager.is_rewards_period_finished()

    # validate that both depositors earned rewards according to their parts in reserve
    depositor1_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor1)
    depositor1_expected_reward = int(0.25 *
                                     10 ** 18 * Wei('1000 ether') / asteth.totalSupply())

    print('Depositor 1 after withdraw:', depositor1_actual_reward)

    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_expected_reward = depositor2_actual_reward + int(0.5 *
                                                                asteth.balanceOf(depositor2) * Wei('1000 ether') / asteth.totalSupply())
    depositor2_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor2)

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('20 ether'))

    # Depositor3 deposit StETH into the reserve
    steth.approve(lending_pool, '1000 ether', {'from': depositor3})
    deposit3 = Wei('1 ether')
    lending_pool.deposit(steth, deposit3, depositor3,
                         0, {'from': depositor3})
    assert is_almost_equal(asteth.balanceOf(depositor3), deposit1)
    assert is_almost_equal(steth.balanceOf(depositor3), 0)

    # start next rewards period
    ldo.transfer(rewards_manager, '1000 ether', {'from': agent})
    assert ldo.balanceOf(rewards_manager) == Wei('1000 ether')
    rewards_manager.start_next_rewards_period(
        {'from': rewards_initializer})
    assert ldo.balanceOf(rewards_manager) == 0

    # Wait till the end of reward period
    chain.sleep(30 * 24 * 60 * 60)
    chain.mine()

    # validate that both depositors earned rewards according to their parts in reserve
    depositor3_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor3)
    depositor3_expected_reward = int(500 * 10 ** 18)

    assert is_almost_equal(depositor3_actual_reward,
                           depositor3_expected_reward, Wei('0.002 ether'))

    depositor2_expected_reward = 1600 * 10 ** 18
    depositor2_actual_reward = incentives_controller.getRewardsBalance(
        [asteth.address], depositor2)

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('20 ether'))
