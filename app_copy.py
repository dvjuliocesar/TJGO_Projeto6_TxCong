from flask import Flask, request, render_template, session
from util_copy import ProcessosAnalisador

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'chave_secreta_segura_jurimetria'

# Inicializa a classe ProcessosAnalisador com o arquivo CSV
try:
    # Ajuste o nome do arquivo conforme necessário
    analisador = ProcessosAnalisador("results_concat/tx_cong_anual_serv.csv")
    print("Analisador inicializado com sucesso")
    
    # Mostrar informações de debug
    comarcas = analisador.obter_comarcas_disponiveis()
    anos = analisador.obter_anos_disponiveis()
    print(f"Comarcas disponíveis ({len(comarcas)}): {comarcas[:5]}...")
    print(f"Anos disponíveis: {anos}")
    
except Exception as e:
    print(f"Erro ao inicializar analisador: {e}")
    import traceback
    traceback.print_exc()
    analisador = None

@app.route('/')
def tabela():
    # Verificar se o analisador foi inicializado
    if not analisador or analisador.df.empty:
        return render_template('erro.html', mensagem="Erro ao carregar dados. Verifique o arquivo CSV.")
    
    # Parâmetros com valores padrão
    filtro_comarca = request.args.get('comarca', '')
    filtro_ano_str = request.args.get('ano', '')
    
    # Obter listas disponíveis
    comarcas = analisador.obter_comarcas_disponiveis()
    anos = analisador.obter_anos_disponiveis()
    
    # Verificar se temos dados
    if not comarcas:
        return render_template('erro.html', mensagem="Nenhuma comarca encontrada no arquivo CSV.")
    
    # Definir valores padrão se não houver seleção
    if not filtro_comarca and comarcas:
        filtro_comarca = comarcas[0]
    
    if not filtro_ano_str and anos:
        filtro_ano = anos[0] if anos else 2020
    else:
        try:
            filtro_ano = int(filtro_ano_str)
        except ValueError:
            filtro_ano = anos[0] if anos else 2020
    
    # Salva na sessão para persistência básica
    session['last_comarca'] = filtro_comarca
    session['last_ano'] = filtro_ano
    
    # Obter dados filtrados
    dados_filtrados = analisador.obter_dados_filtrados(filtro_comarca, filtro_ano)
    
    tabela_html = ""
    if not dados_filtrados.empty:
        # Formatação HTML com Bootstrap
        tabela_html = dados_filtrados.to_html(
            classes='table table-striped table-bordered table-hover',
            index=False,
            float_format=lambda x: f'{x:.2f}' if isinstance(x, (int, float)) else str(x)
        )
    else:
        tabela_html = f"<div class='alert alert-warning'>Sem dados para a comarca '{filtro_comarca}' no ano {filtro_ano}.</div>"
    
    return render_template(
        'base.html',
        tabela_html=tabela_html,
        comarcas=comarcas,
        anos=anos,
        selected_comarca=filtro_comarca,
        selected_ano=filtro_ano
    )

@app.route('/grafico_linha')
def grafico_linha():
    # Verificar se o analisador foi inicializado
    if not analisador or analisador.df.empty:
        return render_template('erro.html', mensagem="Erro ao carregar dados. Verifique o arquivo CSV.")
    
    # Recupera listas
    comarcas = analisador.obter_comarcas_disponiveis()
    
    if not comarcas:
        return render_template('erro.html', mensagem="Nenhuma comarca encontrada no arquivo CSV.")
    
    # Recupera Comarca
    filtro_comarca = request.args.get('comarca', '')
    if not filtro_comarca and comarcas:
        filtro_comarca = comarcas[0]
    
    # Gera figura
    fig = analisador.plotar_graficos_comarca(filtro_comarca)
    
    if fig:
        figura_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        figura_html = "<div class='alert alert-warning'>Não foi possível gerar o gráfico</div>"
    
    return render_template(
        'grafico_linha.html',
        figura_html=figura_html,
        comarcas=comarcas,
        selected_comarca=filtro_comarca
    )

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)