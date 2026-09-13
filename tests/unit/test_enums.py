from app.domain.enums import StatusOrdemServico, TRANSICOES_VALIDAS


class TestStatusOrdemServico:
    def test_todos_status_existem(self):
        assert StatusOrdemServico.RECEBIDA.value == "recebida"
        assert StatusOrdemServico.EM_DIAGNOSTICO.value == "em_diagnostico"
        assert StatusOrdemServico.AGUARDANDO_APROVACAO.value == "aguardando_aprovacao"
        assert StatusOrdemServico.EM_EXECUCAO.value == "em_execucao"
        assert StatusOrdemServico.FINALIZADA.value == "finalizada"
        assert StatusOrdemServico.ENTREGUE.value == "entregue"
        assert StatusOrdemServico.CANCELADA.value == "cancelada"

    def test_transicao_recebida(self):
        permitidas = TRANSICOES_VALIDAS[StatusOrdemServico.RECEBIDA]
        assert StatusOrdemServico.EM_DIAGNOSTICO in permitidas
        assert StatusOrdemServico.CANCELADA in permitidas
        assert StatusOrdemServico.FINALIZADA not in permitidas

    def test_transicao_em_diagnostico(self):
        permitidas = TRANSICOES_VALIDAS[StatusOrdemServico.EM_DIAGNOSTICO]
        assert StatusOrdemServico.AGUARDANDO_APROVACAO in permitidas
        assert StatusOrdemServico.CANCELADA in permitidas

    def test_transicao_aguardando_aprovacao(self):
        permitidas = TRANSICOES_VALIDAS[StatusOrdemServico.AGUARDANDO_APROVACAO]
        assert StatusOrdemServico.EM_EXECUCAO in permitidas
        assert StatusOrdemServico.CANCELADA in permitidas

    def test_transicao_em_execucao(self):
        permitidas = TRANSICOES_VALIDAS[StatusOrdemServico.EM_EXECUCAO]
        assert StatusOrdemServico.FINALIZADA in permitidas
        assert len(permitidas) == 1

    def test_transicao_finalizada(self):
        permitidas = TRANSICOES_VALIDAS[StatusOrdemServico.FINALIZADA]
        assert StatusOrdemServico.ENTREGUE in permitidas
        assert len(permitidas) == 1

    def test_transicao_entregue_sem_saida(self):
        permitidas = TRANSICOES_VALIDAS[StatusOrdemServico.ENTREGUE]
        assert len(permitidas) == 0

    def test_transicao_cancelada_sem_saida(self):
        permitidas = TRANSICOES_VALIDAS[StatusOrdemServico.CANCELADA]
        assert len(permitidas) == 0
