from brownie.network import chain, history
from brownie import ZERO_ADDRESS, Wei
from conftest import load_dependency_contract


def is_almost_equal(a, b, epsilon=100):
    return abs(a - b) < epsilon


def test_incentives(Contract, IncentivesController, ERC20TokenIncentivesController, emission_manager, owner, ldo, agent, depositors, scaled_balane_token_mock, lending_pool_configurator, pool_admin, lending_pool, steth):
    # deploy incentives controller
    incentives_controller = IncentivesController.deploy(ldo, emission_manager, {
        'from': owner})

    # deploy AStETH
    AStETH = load_dependency_contract('AStETH')
    asteth_impl = AStETH.deploy(
        '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9',  # lending pool,
        '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # underlying asset
        ZERO_ADDRESS,  # treasury,
        'AAVE stETH',
        'astETH',
        incentives_controller,
        {'from': owner})

    # deploy VariableDebtStETH
    VariableDebtStETH = load_dependency_contract('VariableDebtStETH')
    variable_debt_steth_impl = VariableDebtStETH.deploy(
        '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9',  # lending pool,
        '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # underlying asset
        'Variable debt stETH',
        'variableDebtStETH',
        ZERO_ADDRESS,
        {'from': owner}
    )

    # deploy StableDebtStETH
    StableDebtStETH = load_dependency_contract('StableDebtStETH')
    stable_debt_steth_impl = StableDebtStETH.deploy(
        '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9',  # lending pool,
        '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # underlying asset
        'Variable debt stETH',
        'variableDebtStETH',
        ZERO_ADDRESS,
        {'from': owner}
    )

    # init reserve in lending pool
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
    asteth = Contract.from_abi('AStETH', asteth, AStETH.abi)

    # initialize asteth reference to debt token
    asteth.initializeDebtToken({'from': owner})

    # get variable debt steth with proxy
    variable_debt_steth = Contract.from_abi(
        'VariableDebtStETH', variable_debt_steth_address, VariableDebtStETH.abi)

    # get stable debt steth with proxy
    stable_debt_steth = Contract.from_abi(
        'StableDebtStETH', stable_debt_steth_address, StableDebtStETH.abi)

    # set staking token
    incentives_controller.setStakingToken(asteth, {'from': owner})
    print('Asteth', asteth)

    [depositor1, depositor2, depositor3] = depositors
    # depositor1 send ether into the pool
    steth.approve(lending_pool, '100 ether', {'from': depositor1})
    deposit1 = Wei('1 ether')
    lending_pool.deposit(steth, deposit1, depositor1,
                         0, {'from': depositor1})
    assert is_almost_equal(asteth.balanceOf(depositor1), deposit1)
    assert is_almost_equal(steth.balanceOf(depositor1), 0)

    chain.sleep(7 * 24 * 60 * 60)
    chain.mine()

    # start reward period
    incentives_controller.setRewardsDuration(30 * 24 * 60 * 60)
    ldo.transfer(emission_manager, '1000 ether', {'from': agent})
    ldo.approve(incentives_controller, '1000 ether',
                {'from': emission_manager})
    incentives_controller.startRewardPeriod(
        '1000 ether', emission_manager, {'from': emission_manager})

    # depositor2 send ether into the pool
    steth.approve(lending_pool, '100 ether', {'from': depositor2})
    deposit2 = Wei('0.5 ether')
    tx = lending_pool.deposit(steth, deposit2, depositor2,
                              0, {'from': depositor2})

    assert is_almost_equal(steth.balanceOf(depositor2), Wei('0.5 ether'))
    assert is_almost_equal(asteth.balanceOf(depositor2), deposit2)

    # wait for half of the reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()

    # validate that both depositors earned rewards according to their parts in reserve
    depositor1_actual_reward = incentives_controller.earned(depositor1)
    depositor1_expected_reward = int(0.5 *
                                     asteth.balanceOf(depositor1) * Wei('1000 ether') / asteth.totalSupply())
    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_actual_reward = incentives_controller.earned(depositor2)
    depositor2_expected_reward = int(0.5 *
                                     asteth.balanceOf(depositor2) * Wei('1000 ether') / asteth.totalSupply())

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    print('Depositor 1:', depositor1_actual_reward)
    print('Depositor 2', depositor2_actual_reward)

    # wait till the end of the reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()

    # validate that both depositors earned rewards according to their parts in reserve
    depositor1_actual_reward = incentives_controller.earned(depositor1)
    depositor1_expected_reward = int(
        asteth.balanceOf(depositor1) * Wei('1000 ether') / asteth.totalSupply())
    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_actual_reward = incentives_controller.earned(depositor2)
    depositor2_expected_reward = int(
        asteth.balanceOf(depositor2) * Wei('1000 ether') / asteth.totalSupply())

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    print('Depositor 1:', depositor1_actual_reward)
    print('Depositor 2', depositor2_actual_reward)

    # depositor1 claims rewards
    assert ldo.balanceOf(depositor1) == 0
    incentives_controller.claimReward(
        {'from': depositor1})
    assert ldo.balanceOf(depositor1) == depositor1_actual_reward
    assert incentives_controller.earned(depositor1) == 0

    ldo.transfer(emission_manager, '1000 ether', {'from': agent})
    ldo.approve(incentives_controller, '1000 ether',
                {'from': emission_manager})
    print(incentives_controller.periodFinish())
    print(chain[-1].timestamp)
    incentives_controller.startRewardPeriod(
        '1000 ether', emission_manager, {'from': emission_manager})

    # depositor2 makes another deposit
    print('Depositor2 reward before deposit:',
          incentives_controller.earned(depositor2))
    print('Depositor2 scaled balance and scaled totalSupply before deposit',
          asteth.getScaledUserBalanceAndSupply(depositor2))
    print('scaledTotalSupply before deposit:', asteth.scaledTotalSupply())
    print()
    deposit2 = Wei('0.5 ether')
    tx = lending_pool.deposit(steth, deposit2, depositor2,
                              0, {'from': depositor2})
    print('Depositor2 reward after deposit:', incentives_controller.earned(
        depositor2))

    print('Depositor2 scaled balance and scaled totalSupply after deposit',
          asteth.getScaledUserBalanceAndSupply(depositor2))
    print('scaledTotalSupply after deposit:', asteth.scaledTotalSupply())

    print()
    depositor2_actual_reward = incentives_controller.earned(
        depositor2)
    print('depositor2_actual_reward:', depositor2_actual_reward)

    # deploy erc20 incentives controller
    # erc20ic = ERC20TokenIncentivesController.deploy(
    #     ldo, owner, {'from': owner}
    # )

    # erc20ic.configureAssets([scaled_balane_token_mock], [])

    # # start reward period
    # incentives_controller.setRewardsDuration(30 * 24 * 60 * 60)
    # ldo.approve(incentives_controller, '1000 ether', {'from': agent})
    # incentives_controller.startRewardPeriod('1000 ether', agent)

    # # chain.sleep(15 * 24 * 60 * 60)
    # # chain.mine()
    # [s1, s2] = depositors

    # # mint tokens
    # scaled_balane_token_mock.mint(s1, '100 ether')
    # incentives_controller.handleAction(s1, '0 ether', '100 ether')

    # scaled_balane_token_mock.mint(s2, '50 ether')
    # incentives_controller.handleAction(s2, '100 ether', '50 ether')
    # #

    # # stake
    # # incentives_controller.stake(s1, '100 ether', {'from': s1})
    # # incentives_controller.stake(s2, '50 ether', {'from': s2})

    # chain.sleep(15 * 24 * 60 * 60)
    # chain.mine()
    # print('earned by s1', incentives_controller.earned(s1))
    # print('earned by s2', incentives_controller.earned(s2))
    # chain.sleep(15 * 24 * 60 * 60)
    # chain.mine()
    # print('earned by s1', incentives_controller.earned(s1))
    # print('earned by s2', incentives_controller.earned(s2))
