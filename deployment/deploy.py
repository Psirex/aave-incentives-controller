from brownie import ERC20TokenIncentivesController
from brownie import ZERO_ADDRESS


def deploy_implementation(reward_token, emission_manager, tx_params):
    return ERC20TokenIncentivesController.deploy(
        reward_token, emission_manager, tx_params)


# def deploy_and_init_proxy(admin, implementation, tx_params):
#     proxy = InitializableAdminUpgradeabilityProxy.deploy(tx_params)
#     proxy.initialize(implementation, admin,
#                      implementation.initialize.encode_input(ZERO_ADDRESS), tx_params)
#     return proxy
