"""Testes das opções de modo da linha de comando."""

import pytest

import main


def test_modo_humano_e_o_padrao(monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py"])

    args = main.parse_args()

    assert args.bot is False
    assert args.human is False


def test_flag_bot(monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py", "--bot", "--seed", "42"])

    args = main.parse_args()

    assert args.bot is True
    assert args.seed == 42


def test_flag_visual(monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py", "--bot", "--visual"])

    args = main.parse_args()

    assert args.visual is True


def test_bot_e_human_nao_podem_ser_usados_juntos(monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py", "--bot", "--human"])

    with pytest.raises(SystemExit):
        main.parse_args()

def test_sem_energia_e_sem_estrategia_por_padrao(monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py"])

    args = main.parse_args()

    assert args.energia is None
    assert args.estrategia is None


def test_flag_energia_e_estrategia(monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py", "--bot", "--energia", "20",
                                     "--estrategia", "limiar_25"])

    args = main.parse_args()

    assert args.energia == 20
    assert args.estrategia == "limiar_25"


def test_energia_sozinha_vale_no_modo_humano(monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py", "--energia", "20"])

    assert main.parse_args().energia == 20


@pytest.mark.parametrize("argv", [
    ["--estrategia", "guloso", "--energia", "20"],
    ["--bot", "--estrategia", "guloso"],
    ["--bot", "--energia", "20", "--estrategia", "inexistente"],
    ["--energia", "0"],
])
def test_combinacoes_invalidas_sao_recusadas(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["main.py", *argv])

    with pytest.raises(SystemExit):
        main.parse_args()
