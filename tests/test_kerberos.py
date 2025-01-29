from operator import itemgetter

import pytest

from testinfra import host

testinfra_hosts = ["ldap"]


@pytest.fixture(scope="module")
def admin_credentials(host: host.Host) -> tuple:
    return itemgetter("kadmin_principal", "kadmin_password")(
        host.ansible.get_variables()
    )


def test_krb5_server_is_installed(host: host.Host):
    krb5 = host.package("krb5-server")
    assert krb5.is_installed


def test_kdc_is_running(host: host.Host):
    kdc = host.service("krb5kdc")
    assert kdc.is_running
    assert kdc.is_enabled


def test_kinit_kadmin_kdestroy_is_working(
    host: host.Host, admin_credentials: tuple, realm: str
):
    kadmin_principal, kadmin_password = admin_credentials
    kadmin_principal = kadmin_principal.replace("{{ realm }}", realm)
    host.run_expect([0], f'kinit "{kadmin_principal}" <<< "{kadmin_password}"')
    try:
        host.run_expect([0], f'kadmin list_principals <<< "{kadmin_password}"')
    finally:
        host.run_expect([0], "kdestroy")
