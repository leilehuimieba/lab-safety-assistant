from __future__ import annotations

import fix_embedding_host_mapping as fehm


def test_pick_container_ip_prefers_named_network() -> None:
    networks = {
        "bridge": {"IPAddress": "172.17.0.10"},
        "docker_default": {"IPAddress": "172.20.0.12"},
    }
    assert fehm.pick_container_ip(networks, preferred_network="docker_default") == "172.20.0.12"


def test_pick_container_ip_falls_back_to_first_available() -> None:
    networks = {
        "network_a": {"IPAddress": ""},
        "network_b": {"IPAddress": "10.0.0.9"},
    }
    assert fehm.pick_container_ip(networks, preferred_network="docker_default") == "10.0.0.9"


def test_pick_container_ip_returns_empty_when_missing() -> None:
    assert fehm.pick_container_ip({}, preferred_network="docker_default") == ""
