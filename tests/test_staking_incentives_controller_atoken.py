from brownie import ZERO_ADDRESS, Wei
from brownie.network import chain
from conftest import load_dependency_contract
from utils import deploy_incentives_controller, init_reserve, is_almost_equal, make_deposit, print_rewards


def test_erc20_incentives_controller_atoken(Contract, IncentivesController, lending_pool_configurator, lending_pool, owner, ldo, pool_admin,
                                            depositors, steth, agent, emission_manager):
    """
    User story:
        1. Depositor1 deposits 1 stETH into lending pool
        2. Depositor2 deposits 0.5 stETH into lending pool
        3. Wait one month before incentives controller launch
        4. Start new rewards period with distribution of 1000 ldo
        5. Wait half of the reward period
        6. Validate that each depositor gained expected amount of rewards
        7. Depositor2 deposits 0.5 stETH
        8. Validate that amount of rewards doesn't chaged
        9. Validate that each depositor gained expected amount of rewards
        10. Claim rewards
    """
    # deploy incentives controller
    incentives_controller = IncentivesController.deploy(ldo, emission_manager, {
        'from': owner})

    [atoken, variable_debt_token, stable_debt_token] = init_reserve(
        Contract=Contract,
        atoken_contract_name='AToken',
        variable_debt_token_contract_name='VariableDebtToken',
        stable_debt_token_contract_name='StableDebtToken',
        lending_pool_configurator=lending_pool_configurator,
        lending_pool=lending_pool,
        incentives_controller=incentives_controller,
        owner=owner,
        pool_admin=pool_admin
    )
    incentives_controller.setStakingToken(atoken, {'from': owner})

    [depositor1, depositor2] = depositors[0:2]

    # 1. Depositor1 deposits 1 stETH into lending pool
    deposit1 = Wei('1 ether')
    make_deposit(lending_pool, steth, atoken, depositor1, deposit1)

    # 2. Depositor2 deposits 0.5 stETH into lending pool
    deposit2 = Wei('0.5 ether')
    make_deposit(lending_pool, steth, atoken, depositor2, deposit2)

    # 3. Wait one month before incentives controller launch
    chain.sleep(30 * 24 * 60 * 60)
    chain.mine()

    # 4. Start new rewards period with distribution of 1000 ldo
    incentives_controller.setRewardsDuration(30 * 24 * 60 * 60)
    ldo.transfer(emission_manager, '1000 ether', {'from': agent})
    ldo.approve(incentives_controller, '1000 ether',
                {'from': emission_manager})
    incentives_controller.startRewardPeriod(
        '1000 ether', emission_manager, {'from': emission_manager})

    # 5. Wait half of the reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()

    # 6. Validate that each depositor gained expected amount of rewards
    depositor1_actual_reward = incentives_controller.earned(depositor1)
    depositor1_expected_reward = Wei('333.3333 ether')
    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_actual_reward = incentives_controller.earned(depositor2)
    depositor2_expected_reward = Wei('166.6666 ether')

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    print('Rewards after half of the period')
    print_rewards('Depositor1', depositor1_actual_reward,
                  depositor1_expected_reward)
    print_rewards('Depositor2', depositor2_actual_reward,
                  depositor2_expected_reward)

    # # 6.5 Depositor1 claims rewards
    # incentives_controller.claimReward({'from': depositor1})
    # print('Depositor1 received LDO:', ldo.balanceOf(depositor1))
    # print_rewards('Depositor1', incentives_controller.earned(
    #     depositor1), depositor1_expected_reward)

    # 7. Depositor2 deposits 0.5 stETH
    make_deposit(lending_pool, steth, atoken, depositor2, deposit2)

    print('Rewards after Depositor2 makes second deposit:')
    print_rewards('Depositor1', incentives_controller.earned(
        depositor1), depositor1_expected_reward)
    print_rewards('Depositor2', incentives_controller.earned(
        depositor2), depositor2_expected_reward)

    # 8. Wait till the end of reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()

    # 9. Validate that each depositor gained expected amount of rewards
    depositor1_actual_reward = incentives_controller.earned(depositor1)

    # Wei('250 ether') in case when 6.5 step active
    depositor1_expected_reward = Wei('583.3333 ether')
    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_actual_reward = incentives_controller.earned(depositor2)
    depositor2_expected_reward = Wei('416.6666 ether')

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    print('Rewards after end of rewards period')
    print_rewards('Depositor1', depositor1_actual_reward,
                  depositor1_expected_reward)
    print_rewards('Depositor2', depositor2_actual_reward,
                  depositor2_expected_reward)

    # 10. Claim rewards
    incentives_controller.claimReward({'from': depositor1})
    print('Depositor1 received LDO:', ldo.balanceOf(depositor1))
    print_rewards('Depositor1', incentives_controller.earned(
        depositor1), depositor1_expected_reward)

    chain.mine()
    incentives_controller.claimReward({'from': depositor2})
    print('Depositor2 received LDO:', ldo.balanceOf(depositor2))
    print_rewards('Depositor2', incentives_controller.earned(
        depositor2), depositor2_expected_reward)
