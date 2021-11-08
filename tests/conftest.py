import pytest
from deployment.deploy import deploy_implementation
from brownie import ZERO_ADDRESS, project, config
from pathlib import Path

AGENT = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'

aave_project = None


def load_dependency_contract(name):
    global aave_project
    if aave_project is None:
        aave_project = project.load(Path.home() / ".brownie" /
                                    "packages" / config["dependencies"][0])
    return getattr(aave_project, name)


@pytest.fixture(scope='module')
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope='module')
def admin(accounts):
    return accounts[1]


@pytest.fixture(scope='module')
def emission_manager(accounts):
    return accounts[2]


@pytest.fixture(scope='module')
def rewards_initializer(accounts):
    return accounts[3]


@pytest.fixture(scope='module')
def depositors(accounts, steth):
    depositors = accounts[4:7]
    for depositor in depositors:
        depositor.transfer(steth, '1 ether')
    return depositors


@pytest.fixture(scope='module')
def pool_admin(accounts):
    return accounts.at('0xEE56e2B3D491590B5b31738cC34d5232F378a8D5', force=True)


@pytest.fixture(scope='module')
def ldo(interface):
    return interface.ERC20('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32')


@pytest.fixture(scope='module')
def scaled_balane_token_mock(ScaledBalanceTokenMock, owner):
    return ScaledBalanceTokenMock.deploy({'from': owner})


@pytest.fixture(scope='module')
def agent(accounts):
    return accounts.at(AGENT, force=True)


@pytest.fixture(scope='module')
def proxy_factory(owner):
    InitializableAdminUpgradeabilityProxy = load_dependency_contract(
        'InitializableAdminUpgradeabilityProxy')

    def factory():
        return InitializableAdminUpgradeabilityProxy.deploy({'from': owner})
    return factory


@pytest.fixture(scope='module')
def implementation(owner, ldo, rewards_manager):
    return deploy_implementation(
        ldo, rewards_manager, {'from': owner})


@pytest.fixture(scope='module')
def incentives_controller(Contract, ERC20TokenIncentivesController, proxy_factory, owner, admin, implementation):
    proxy = proxy_factory()
    proxy.initialize(
        implementation, admin, implementation.initialize.encode_input(
            ZERO_ADDRESS)
    )
    return Contract.from_abi("ERC20TokenIncentivesController", proxy, ERC20TokenIncentivesController.abi)


@pytest.fixture(scope='module')
def rewards_manager(owner, RewardsManager, rewards_initializer, scaled_balane_token_mock):
    return RewardsManager.deploy(rewards_initializer, {'from': owner})


@pytest.fixture(scope='module')
def lending_pool_configurator(interface):
    return interface.LendingPoolConfigurator('0x311Bb771e4F8952E6Da169b425E7e92d6Ac45756')


@pytest.fixture(scope='module')
def asteth_impl(Contract, owner, proxy_factory, admin, incentives_controller):
    AStETH = load_dependency_contract('AStETH')
    asteth = AStETH.deploy(
        '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9',  # lending pool,
        '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # underlying asset
        ZERO_ADDRESS,  # treasury,
        'AAVE stETH',
        'astETH',
        incentives_controller,
        {'from': owner})
    asteth.initialize(
        18,
        'AAVE stETH',
        'astETH',
        {'from': owner}
    )
    return asteth


@pytest.fixture(scope='module')
def variable_debt_steth_impl(Contract, owner, admin, incentives_controller, proxy_factory):
    VariableDebtStETH = load_dependency_contract('VariableDebtStETH')
    variable_debt_steth = VariableDebtStETH.deploy(
        '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9',  # lending pool,
        '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # underlying asset
        'Variable debt stETH',
        'variableDebtStETH',
        ZERO_ADDRESS,
        {'from': owner}
    )

    variable_debt_steth.initialize(
        18,
        'Variable debt stETH',
        'variableDebtStETH',
        {'from': owner}
    )
    return variable_debt_steth


@pytest.fixture(scope='module')
def stable_debt_steth_impl(Contract, owner, admin, incentives_controller, proxy_factory):
    StableDebtStETH = load_dependency_contract('StableDebtStETH')
    stable_debt_steth = StableDebtStETH.deploy(
        '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9',  # lending pool,
        '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # underlying asset
        'Variable debt stETH',
        'variableDebtStETH',
        ZERO_ADDRESS,
        {'from': owner}
    )

    stable_debt_steth.initialize(
        18,
        'Variable debt stETH',
        'variableDebtStETH',
        {'from': owner}
    ),
    return stable_debt_steth


@pytest.fixture(scope='module')
def lending_pool(interface):
    return interface.LendingPool('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9')


@pytest.fixture(scope='module')
def steth(interface):
    return interface.StETH('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')
