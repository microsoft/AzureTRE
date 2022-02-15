import ipaddress
import pytest
from mock import patch

import services.cidr_service

generate_new_cidr_test_data = [
    (["10.2.4.0/24", "10.1.0.0/16", "10.2.1.0/24", "10.2.3.0/24", "10.2.0.0/24", "10.2.2.0/24"], 24, "10.2.5.0/24"),
    (["10.2.4.0/24", "10.1.0.0/16", "10.2.1.0/24", "10.2.3.0/24", "10.2.0.0/24", "10.2.2.0/24"], 16, "10.3.0.0/16"),
    (["10.1.0.0/16"], 24, "10.2.0.0/24"),
    (["10.1.0.0/16"], 16, "10.2.0.0/16"),
    (["10.1.0.0/16", "10.2.1.0/24"], 24, "10.2.0.0/24"),
    (["10.2.1.0/24", "10.1.0.0/16"], 16, "10.3.0.0/16"),
    (["10.1.0.0/16", "10.5.1.0/24"], 16, "10.4.0.0/16"),
    (["10.2.1.0/24", "10.1.0.0/16"], 20, "10.2.16.0/20"),
]


@pytest.mark.parametrize("input_addresses, input_network_size, expected_cidr", generate_new_cidr_test_data)
@patch('core.config.CORE_ADDRESS_SPACE', "10.0.0.0/16")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
def test_generate_new_cidr__returns_currect_block(input_addresses, input_network_size, expected_cidr):
    assert expected_cidr == services.cidr_service.generate_new_cidr(input_addresses, input_network_size)


@patch('core.config.CORE_ADDRESS_SPACE', "10.5.0.0/16")
def test_generate_new_cidr__invalid_netmask_raises_exception():
    with pytest.raises(ipaddress.NetmaskValueError):
        services.cidr_service.generate_new_cidr(["10.2.1.0/24", "10.1.0.0/16"], 50)


@patch('core.config.CORE_ADDRESS_SPACE', "10.5.0.0/16")
def test_generate_new_cidr__invalid_network_raises_exception():
    with pytest.raises(ipaddress.AddressValueError):
        services.cidr_service.generate_new_cidr(["10.1.0.300/16"], 24)


@patch('core.config.CORE_ADDRESS_SPACE', "10.0.0.0/16")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
def test_is_network_available__returns_false():
    assert False is services.cidr_service.is_network_available([], "10.0.0.0/16")


@patch('core.config.CORE_ADDRESS_SPACE', "10.0.0.0/16")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
def test_is_network_available__returns_true():
    assert True is services.cidr_service.is_network_available(["10.2.4.0/24", "10.1.0.0/16", "10.2.1.0/24", "10.2.3.0/24", "10.2.0.0/24", "10.2.2.0/24"], "10.2.5.0/24")
