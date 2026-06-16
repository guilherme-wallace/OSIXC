ACOES_DESTRUTIVAS_HABILITADAS = False


def bloquear_acao_destrutiva(nome_acao):
    if not ACOES_DESTRUTIVAS_HABILITADAS:
        raise RuntimeError(
            f"Acao destrutiva bloqueada nesta etapa da refatoracao: {nome_acao}. "
            "Valide primeiro o relatorio CSV gerado em dry-run."
        )
