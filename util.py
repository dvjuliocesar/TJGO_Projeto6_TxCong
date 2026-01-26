import numpy as np
import pandas as pd
import plotly.express as px
import glob
import os

class ProcessosAnalisador:
    def __init__(self, arquivo_csv):
        # Permite passar um caminho fixo ou busca padrão
        self.df = self._carregar_dados(arquivo_csv)
    
    def _carregar_dados(self, arquivo_csv):
       # Listar os arquivos CSV na pasta 'uploads'
        arquivo_csv = glob.glob('uploads/processos_*.csv')
        # Carregar os arquivos CSV e concatenar em um único DataFrame
        dfs = []
        for arquivo in arquivo_csv:  # lista/iterável com os caminhos tipo 'processos_1.csv', 'processos_2.csv', ...
            df_ano = pd.read_csv(arquivo, sep='#', encoding='utf-8')
            dfs.append(df_ano)

        df = pd.concat(dfs, ignore_index=True)
        
        # Normalização de nomes de colunas (strip e lower para evitar erros)
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Mapeamento de colunas flexível
        mapa_colunas = {
            'data_distribuicao': next((c for c in df.columns if 'distribuicao' in c), 'data_distribuicao'),
            'data_baixa': next((c for c in df.columns if 'baixa' in c), 'data_baixa'),
            'nome_area_acao': next((c for c in df.columns if 'area_acao' in c), 'nome_area_acao'),
            'processo_id': next((c for c in df.columns if 'processo_id' in c), 'processo_id'),
            'comarca': next((c for c in df.columns if 'comarca' in c), 'comarca'),
            'serventia': next((c for c in df.columns if 'serventia' in c), 'serventia')
        }
        
        df = df.rename(columns=mapa_colunas)
        
        # Conversão de datas
        df['data_distribuicao'] = pd.to_datetime(df['data_distribuicao'], errors='coerce')
        df['data_baixa'] = pd.to_datetime(df['data_baixa'], errors='coerce')
        
        # Criação de colunas auxiliares de ano para performance
        df['ano_dist'] = df['data_distribuicao'].dt.year
        df['ano_baixa'] = df['data_baixa'].dt.year
        
        return df
    
    def obter_comarcas_disponiveis(self):
        if self.df.empty: return []
        return sorted(self.df['comarca'].dropna().unique())
    
    def obter_anos_disponiveis(self):
        if self.df.empty: return []
        # Considera anos de distribuição e baixa
        anos_dist = self.df['ano_dist'].dropna().unique()
        anos_baixa = self.df['ano_baixa'].dropna().unique()
        todos_anos = np.unique(np.concatenate((anos_dist, anos_baixa)))
        return sorted([int(x) for x in todos_anos if x > 2016]) # Filtro básico de sanidade
    
    def calcular_estatisticas(self, comarca, ano_selecionado):
        """
        Calcula estatísticas baseadas no Ano de Referência (Jurimetria histórica).
        """
        if self.df.empty: return pd.DataFrame()

        # 1. Filtro base de Comarca
        df_c = self.df[self.df['comarca'] == comarca].copy()
        
        # Se não houver dados da comarca
        if df_c.empty: return pd.DataFrame()

        # 2. Definição das Métricas

        # A) Novos Casos (Distribuídos): Exatamente no ano selecionado
        # Ignora data de baixa.
        distribuidos = df_c[df_c['ano_dist'] == ano_selecionado]
        grp_dist = distribuidos.groupby(['nome_area_acao', 'comarca', 'serventia']).size().rename('Distribuídos')

        # B) Casos Finalizados (Baixados): Exatamente no ano selecionado
        baixados = df_c[df_c['ano_baixa'] == ano_selecionado]
        grp_baix = baixados.groupby(['nome_area_acao', 'comarca', 'serventia']).size().rename('Baixados')

        # C) Pendentes (Acervo Histórico - Opção B):
        # Regra: Processo distribuído ATÉ o ano selecionado E (Não baixado OU Baixado APÓS o ano selecionado)
        # Filtra: (Distribuído no Ano Selecionado) E (Data de Baixa é Nula)
        condicao_pendente = (
            (df_c['ano_dist'] == ano_selecionado) & 
            (df_c['ano_baixa'].isna())
        )

        pendentes = df_c[condicao_pendente]
        grp_pend = pendentes.groupby(['nome_area_acao', 'comarca', 'serventia']).size().rename('Pendentes')

        """condicao_pendente = (
            (df_c['ano_baixa'] <= ano_selecionado) & 
            ( (df_c['ano_baixa'].isna()) | (df_c['ano_baixa'] > ano_selecionado) )
        )
        pendentes = df_c[condicao_pendente]
        grp_pend = pendentes.groupby(['nome_area_acao', 'comarca', 'serventia']).size().rename('Pendentes')"""

        # 3. Consolidação
        df_final = pd.concat([grp_dist, grp_baix, grp_pend], axis=1).fillna(0).astype(int).reset_index()

        # 4. Cálculo da Taxa de Congestionamento
        # Fórmula: Pendentes / (Pendentes + Baixados)
        soma_denominador = df_final['Pendentes'] + df_final['Baixados']
        
        df_final['Taxa de Congestionamento (%)'] = np.where(
            soma_denominador > 0,
            (df_final['Pendentes'] / soma_denominador) * 100,
            0.0
        ).round(2)

        # 5. Linha de Totais
        totais = {
            'nome_area_acao': 'TOTAL',
            'comarca': '',
            'serventia': '',
            'Distribuídos': df_final['Distribuídos'].sum(),
            'Baixados': df_final['Baixados'].sum(),
            'Pendentes': df_final['Pendentes'].sum()
        }
        
        denom_total = totais['Pendentes'] + totais['Baixados']
        totais['Taxa de Congestionamento (%)'] = round(
            (totais['Pendentes'] / denom_total * 100), 2
        ) if denom_total > 0 else 0.0

        df_final = pd.concat([df_final, pd.DataFrame([totais])], ignore_index=True)
        
        return df_final

    def plotar_graficos_ano(self, ano_selecionado): 
        """
        Gera gráfico de barras comparativo de Taxa de Congestionamento por Comarca/Área no Ano X.
        Usa a mesma lógica de 'Resíduo Histórico' da tabela.
        """
        if self.df.empty: return px.bar(title="Sem dados")

        # Preparar dados agregados por Comarca e Área
        # Pendentes (Estoque no ano)
        cond_pend = (
            (self.df['ano_dist'] == ano_selecionado) & 
            (self.df['ano_baixa'].isna())
        )

        """cond_pend = (
            (self.df['ano_dist'] <= ano_selecionado) & 
            ((self.df['ano_baixa'].isna()) | (self.df['ano_baixa'] > ano_selecionado))
        )"""
        
        pendentes = self.df[cond_pend].groupby(['comarca', 'nome_area_acao']).size().rename('pendentes')

        # Baixados (Produção no ano)
        cond_baix = (self.df['ano_baixa'] == ano_selecionado)
        baixados = self.df[cond_baix].groupby(['comarca', 'nome_area_acao']).size().rename('baixados')

        # Merge
        df_agg = pd.concat([pendentes, baixados], axis=1).fillna(0)
        
        # Cálculo Taxa
        df_agg['taxa'] = (df_agg['pendentes'] / (df_agg['pendentes'] + df_agg['baixados'])) * 100
        df_agg = df_agg.fillna(0).round(2).reset_index()

        # Filtrar possíveis infinitos ou NaNs residuais
        df_agg = df_agg[df_agg['taxa'].notna()]

        # Plot
        fig = px.bar(
            df_agg,
            x='comarca',
            y='taxa',
            color='nome_area_acao',
            barmode='group',
            title=f'Taxa de Congestionamento - {ano_selecionado}',
            text_auto='.2f',
            labels={'taxa': 'Taxa de Congestionamento (%)', 'nome_area_acao': 'Área', 'comarca': 'Comarca'}
        )
        
        fig.update_traces(textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', yaxis_range=[0, 110])
        
        return fig

    def plotar_graficos_comarca(self, comarca): 
        """
        Gera gráfico de linha evolutivo.
        Para cada ano, calcula o estoque pendente real naquele momento.
        """
        if self.df.empty: return px.line(title="Sem dados")

        comarca_norm = str(comarca).strip().lower()
        df_c = self.df[self.df['comarca'].str.strip().str.lower() == comarca_norm].copy()

        if df_c.empty:
            return px.line(title=f'Sem dados para a comarca: {comarca}')

        # Determinar intervalo de anos para o gráfico
        min_ano = 2020
        max_ano = 2024 # Ou datetime.now().year
        anos = list(range(min_ano, max_ano + 1))
        
        dados_grafico = []

        # Áreas disponíveis nessa comarca
        areas = df_c['nome_area_acao'].unique()

        for area in areas:
            df_area = df_c[df_c['nome_area_acao'] == area]
            
            for ano in anos:
                # Baixados no ano exato
                n_baixados = len(df_area[df_area['ano_baixa'] == ano])
                
                # Pendentes (Acervo até o final do ano)
                # Distribuídos até o ano E (não baixados OU baixados no futuro)
                cond_pend = (
                    (df_c['ano_dist'] == ano) & 
                    (df_c['ano_baixa'].isna())
                )
                '''cond_pend = (
                    (df_area['ano_dist'] <= ano) & 
                    ((df_area['ano_baixa'].isna()) | (df_area['ano_baixa'] > ano))
                )'''
                n_pendentes = len(df_area[cond_pend])

                if (n_pendentes + n_baixados) > 0:
                    taxa = (n_pendentes / (n_pendentes + n_baixados)) * 100
                else:
                    taxa = 0.0 # ou None para quebrar a linha
                
                # Só adiciona se houver algum movimento histórico (para não plotar anos vazios antes do início)
                # Opcional: remover este if se quiser linha zero desde o início
                if n_pendentes > 0 or n_baixados > 0:
                    dados_grafico.append({
                        'ano': ano,
                        'nome_area_acao': area,
                        'taxa': round(taxa, 2)
                    })

        df_plot = pd.DataFrame(dados_grafico)

        if df_plot.empty:
             return px.line(title=f'Dados insuficientes para gráfico histórico: {comarca}')

        fig = px.line(
            df_plot,
            x='ano',
            y='taxa',
            color='nome_area_acao',
            markers=True,
            title=f'Evolução da Taxa de Congestionamento — {comarca}',
            labels={'ano': 'Ano', 'taxa': 'Taxa de Congestionamento (%)', 'nome_area_acao': 'Área'}
        )
        
        fig.update_layout(
            yaxis_range=[0, 105],
            xaxis=dict(tickmode='linear')
        )
        
        return fig
       
