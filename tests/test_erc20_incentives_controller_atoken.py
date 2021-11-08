from brownie import ZERO_ADDRESS, Wei
from brownie.network import chain
from conftest import load_dependency_contract
from utils import deploy_incentives_controller, init_reserve, is_almost_equal, make_deposit, print_rewards


def test_erc20_incentives_controller_atoken(Contract, lending_pool_configurator, lending_pool, owner, ldo, pool_admin,
                                            depositors, steth, agent, incentives_controller, rewards_manager, rewards_initializer):
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
    rewards_manager.set_asset(atoken, {'from': owner})
    reward_amount = Wei('1000 ether')
    ldo.transfer(rewards_manager, reward_amount, {'from': agent})
    assert ldo.balanceOf(rewards_manager) == reward_amount
    rewards_manager.set_rewards_contract(
        incentives_controller, {'from': owner})
    rewards_manager.set_rewards_period_duration(
        30 * 24 * 60 * 60, {'from': owner})
    rewards_manager.start_next_rewards_period(
        {'from': rewards_initializer})

    # 5. Wait half of the reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()

    # 6. Validate that each depositor gained expected amount of rewards
    depositor1_actual_reward = incentives_controller.getRewardsBalance(
        [atoken], depositor1)
    depositor1_expected_reward = Wei('333.3333 ether')
    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_actual_reward = incentives_controller.getRewardsBalance(
        [atoken], depositor2)
    depositor2_expected_reward = Wei('166.6666 ether')

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    print('Rewards after half of the period')
    print_rewards('Depositor1', depositor1_actual_reward,
                  depositor1_expected_reward)
    print_rewards('Depositor2', depositor2_actual_reward,
                  depositor2_expected_reward)

    # # 6.5 Depositor1 claims rewards
    # incentives_controller.claimRewards(
    #     [atoken], depositor1_actual_reward, depositor1, {'from': depositor1})
    # print('Depositor1 received LDO:', ldo.balanceOf(depositor1))
    # print_rewards('Depositor1', incentives_controller.getRewardsBalance(
    #     [atoken], depositor1), depositor1_expected_reward)

    # 7. Depositor2 deposits 0.5 stETH
    make_deposit(lending_pool, steth, atoken, depositor2, deposit2)

    print('Rewards after Depositor2 makes second deposit:')
    print_rewards('Depositor1', incentives_controller.getRewardsBalance(
        [atoken], depositor1), depositor1_expected_reward)
    print_rewards('Depositor2', incentives_controller.getRewardsBalance(
        [atoken], depositor2), depositor2_expected_reward)

    # 8. Wait till the end of reward period
    chain.sleep(15 * 24 * 60 * 60)
    chain.mine()

    # 9. Validate that each depositor gained expected amount of rewards
    depositor1_actual_reward = incentives_controller.getRewardsBalance(
        [atoken], depositor1)

    # Wei('250 ether') in case when 6.5 step active
    depositor1_expected_reward = Wei('583.3333 ether')
    assert is_almost_equal(depositor1_actual_reward,
                           depositor1_expected_reward, Wei('0.002 ether'))

    depositor2_actual_reward = incentives_controller.getRewardsBalance(
        [atoken], depositor2)
    depositor2_expected_reward = Wei('416.6666 ether')

    assert is_almost_equal(depositor2_actual_reward,
                           depositor2_expected_reward, Wei('0.002 ether'))

    print('Rewards after end of rewards period')
    print_rewards('Depositor1', depositor1_actual_reward,
                  depositor1_expected_reward)
    print_rewards('Depositor2', depositor2_actual_reward,
                  depositor2_expected_reward)

    # 10. Claim rewards
    incentives_controller.claimRewards(
        [atoken], depositor1_actual_reward, depositor1, {'from': depositor1})
    print('Depositor1 received LDO:', ldo.balanceOf(depositor1))
    print_rewards('Depositor1', incentives_controller.getRewardsBalance(
        [atoken], depositor1), depositor1_expected_reward)

    chain.mine()
    incentives_controller.claimRewards(
        [atoken], depositor2_actual_reward, depositor2, {'from': depositor2})
    print('Depositor2 received LDO:', ldo.balanceOf(depositor2))
    print_rewards('Depositor2', incentives_controller.getRewardsBalance(
        [atoken], depositor2), depositor2_expected_reward)
