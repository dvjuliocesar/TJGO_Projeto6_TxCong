from flask import Flask, request, render_template, session
from util import ProcessosAnalisador
import pandas as pd

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'chave_secreta_segura_jurimetria'

# Inicializa a classe ProcessosAnalisador com o arquivo CSV
analisador = ProcessosAnalisador("uploads")

@app.route('/')
def tabela():
    # Parâmetros com valores padrão
    filtro_comarca = request.args.get('comarca', 'GOIANIRA')
    filtro_ano_str = request.args.get('ano', '2020')

    # Validação do Ano
    try:
        filtro_ano = int(filtro_ano_str)
    except ValueError:
        filtro_ano = 2020

    # Salva na sessão para persistência básica (opcional)
    session['last_comarca'] = filtro_comarca
    session['last_ano'] = filtro_ano

    # Dados para os Seletores
    comarcas = analisador.obter_comarcas_disponiveis()
    anos = analisador.obter_anos_disponiveis() # Retorna lista de inteiros
    
    # Se filtro de comarca vier vazio ou inválido, pega o primeiro disponível
    if filtro_comarca not in comarcas and comarcas:
        filtro_comarca = comarcas[0]

    # Cálculo Estatístico
    estatisticas_df = analisador.calcular_estatisticas(filtro_comarca, filtro_ano)

    tabela_html = ""
    if not estatisticas_df.empty:
        # Renomeação final para apresentação
        cols_map = {
            "nome_area_acao": "Área de Ação",
            "comarca": "Comarca",
            "serventia": "Serventia"
        }
        estatisticas_df = estatisticas_df.rename(columns=cols_map)

        # Seleção e Ordem de Colunas
        cols_order = [
            "Área de Ação", "Comarca", "Serventia", 
            "Distribuídos", "Baixados", "Pendentes", 
            "Taxa de Congestionamento (%)"
        ]
        # Garante que as colunas existem antes de filtrar (caso o DF venha vazio ou parcial)
        cols_existentes = [c for c in cols_order if c in estatisticas_df.columns]
        estatisticas_df = estatisticas_df[cols_existentes]

        # Formatação HTML com Bootstrap
        tabela_html = estatisticas_df.to_html(
            classes='table table-striped table-bordered table-hover',
            index=False,
            float_format=lambda x: f'{x:.2f}' # Formatação de float no HTML
        )
    else:
        tabela_html = "<div class='alert alert-warning'>Sem dados para os filtros selecionados.</div>"

    return render_template(
        'base.html',
        tabela_html=tabela_html,
        comarcas=comarcas,
        anos=anos,
        selected_comarca=filtro_comarca,
        selected_ano=filtro_ano
    )

@app.route('/grafico')
def grafico():
    # Recupera ano
    filtro_ano_str = request.args.get('ano', '2020')
    try:
        filtro_ano = int(filtro_ano_str)
    except ValueError:
        filtro_ano = 2020

    # Recupera listas para filtros (caso precise renderizar menu novamente)
    anos = analisador.obter_anos_disponiveis()

    # Gera figura
    fig = analisador.plotar_graficos_ano(filtro_ano)
    
    # Renderiza HTML do Plotly
    figura_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    return render_template(
        'grafico.html',
        figura_html=figura_html,
        anos=anos,
        selected_ano=filtro_ano
    )

@app.route('/grafico_linha')
def grafico_linha():
    # Recupera listas
    comarcas = analisador.obter_comarcas_disponiveis()
    
    # Recupera Comarca
    default_comarca = comarcas[0] if comarcas else ''
    filtro_comarca = request.args.get('comarca', default_comarca)

    # Gera figura
    fig = analisador.plotar_graficos_comarca(filtro_comarca)
    
    figura_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    return render_template(
        'grafico_linha.html',
        figura_html=figura_html,
        comarcas=comarcas,
        selected_comarca=filtro_comarca
    )

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)