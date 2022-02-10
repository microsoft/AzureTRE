from typing import List
from ipaddress import IPv4Network, NetmaskValueError, collapse_addresses

from core import config


def generate_new_cidr(allocated_subnets: List[str], required_cidr_block_type: int) -> str:
    if required_cidr_block_type >= 32 or required_cidr_block_type < 8:
        raise NetmaskValueError("Invalid netmask for this operation.")

    free_subnets = get_free_subnets(allocated_subnets)

    # compare to the required subnet size and work with what is large enough
    free_subnets = [x for x in free_subnets if x.prefixlen <= required_cidr_block_type]

    if len(free_subnets) == 0:
        raise Exception("Not enough space in network.")

    # allocate in smaller subnets before larger ones
    free_subnets.sort(key=lambda x: x.prefixlen, reverse=True)
    allocation_subnet = free_subnets[0]
    new_subnet = list(allocation_subnet.subnets(new_prefix=required_cidr_block_type))
    return str(new_subnet[0])


def get_free_subnets(allocated_subnets: List[str]) -> List[IPv4Network]:
    core_network = IPv4Network(config.CORE_ADDRESS_SPACE)
    allocation_network = IPv4Network(config.TRE_ADDRESS_SPACE)

    free_subnets = remove_subnet([allocation_network], core_network)

    for subnet_string in allocated_subnets:
        free_subnets = remove_subnet(free_subnets, IPv4Network(subnet_string))

    return free_subnets


def is_network_available(allocated_subnets: List[str], requested_CIDR) -> bool:
    requested_network = IPv4Network(requested_CIDR)
    for subnet in get_free_subnets(allocated_subnets):
        if requested_network.subnet_of(subnet):
            return True

    # The requested network does not fit in the network
    return False


def remove_subnet(subnets: List[IPv4Network], exclude: IPv4Network) -> List[IPv4Network]:
    result = []
    # Find which subnet the exclusion is part of
    for sub in subnets:
        # If found, exclude & add the result
        if exclude.subnet_of(sub):
            result.extend(list(sub.address_exclude(exclude)))
        else:
            # Other subnets can be added directly
            result.append(sub)

    # Collapse in case of overlaps
    new_result = list(collapse_addresses(result))
    new_result.sort()
    return new_result
