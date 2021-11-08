from brownie import ZERO_ADDRESS
from conftest import load_dependency_contract

LENDING_POOL_ADDRESS = '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9'
STETH_ADDRESS = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
INTEREST_RATE_STRATEGY_ADDRESS = '0x4ce076b9dD956196b814e54E1714338F18fde3F4'


def deploy_incentives_controller(Contract, ERC20TokenIncentivesController,
                                 RewardsManager, ldo, owner):
    rewards_initializer = admin = owner
    rewards_manager = RewardsManager.deploy(
        rewards_initializer, {'from': owner})
    implementation = ERC20TokenIncentivesController.deploy(
        ldo, rewards_manager, {'from': owner})
    InitializableAdminUpgradeabilityProxy = load_dependency_contract(
        'InitializableAdminUpgradeabilityProxy')

    proxy = InitializableAdminUpgradeabilityProxy.deploy({'from': owner})
    proxy.initialize(
        implementation, admin, implementation.initialize.encode_input(
            ZERO_ADDRESS)
    )
    return [rewards_manager, Contract.from_abi("ERC20TokenIncentivesController", proxy, ERC20TokenIncentivesController.abi)]


def init_reserve(
        Contract, atoken_contract_name, variable_debt_token_contract_name, stable_debt_token_contract_name,
        lending_pool_configurator, lending_pool, incentives_controller, owner, pool_admin):
    # deploy AToken implementation
    AToken = load_dependency_contract(atoken_contract_name)
    atoken_impl = AToken.deploy(
        LENDING_POOL_ADDRESS,  # lending pool,
        STETH_ADDRESS,  # underlying asset
        ZERO_ADDRESS,  # treasury,
        f'AAVE {atoken_contract_name}',
        atoken_contract_name,
        incentives_controller,
        {'from': owner})

    # deploy VariableDebtToken implementation
    VariableDebtToken = load_dependency_contract(
        variable_debt_token_contract_name)
    variable_debt_token_impl = VariableDebtToken.deploy(
        LENDING_POOL_ADDRESS,  # lending pool,
        STETH_ADDRESS,  # underlying asset
        f'Variable debt {variable_debt_token_contract_name}',
        variable_debt_token_contract_name,
        ZERO_ADDRESS,
        {'from': owner}
    )

    # deploy StableDebtToken token implementation
    StableDebtToken = load_dependency_contract(stable_debt_token_contract_name)
    stable_debt_token_impl = StableDebtToken.deploy(
        LENDING_POOL_ADDRESS,  # lending pool,
        STETH_ADDRESS,  # underlying asset
        f'Variable debt {stable_debt_token_contract_name}',
        stable_debt_token_contract_name,
        ZERO_ADDRESS,
        {'from': owner}
    )

    # init StETH reserve in lending pool
    lending_pool_configurator.initReserve(
        atoken_impl,
        stable_debt_token_impl,
        variable_debt_token_impl,
        18,
        INTEREST_RATE_STRATEGY_ADDRESS,  # interest rate strategy WETH
        {'from': pool_admin})

    reserve_data = lending_pool.getReserveData(STETH_ADDRESS)
    [atoken_address, stable_debt_token_address,
        variable_debt_token_address] = reserve_data[7:10]

    # get proxied AStETH
    atoken = Contract.from_abi('AStETH', atoken_address, AToken.abi)

    # get proxied VariableDebtStETH
    variable_debt_token = Contract.from_abi(
        'VariableDebtStETH', variable_debt_token_address, VariableDebtToken.abi)

    # get proxied StableDebtStETH
    stable_debt_token = Contract.from_abi(
        'StableDebtStETH', stable_debt_token_address, StableDebtToken.abi)

    return [atoken, variable_debt_token, stable_debt_token]


def make_deposit(lending_pool, steth, atoken, depositor, amount):
    steth_balance_before_deposit = steth.balanceOf(depositor)
    atoken_balance_before_deposit = atoken.balanceOf(depositor)
    steth.approve(lending_pool, amount, {'from': depositor})
    lending_pool.deposit(steth, amount, depositor,
                         0, {'from': depositor})
    assert is_almost_equal(atoken.balanceOf(depositor),
                           atoken_balance_before_deposit + amount)
    assert is_almost_equal(steth_balance_before_deposit -
                           amount, steth.balanceOf(depositor))


def is_almost_equal(a, b, epsilon=100):
    return abs(a - b) < epsilon


def print_rewards(depositor, actual_reward, expected_reward):
    print(f'{depositor} actual reward:', actual_reward)
    print(f'{depositor} expected reward:', expected_reward)
    print()
