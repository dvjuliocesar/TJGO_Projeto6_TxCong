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
        arquivo_csv = glob.glob('dataclean/processos_*.csv')
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
        return sorted([int(x) for x in todos_anos if x >= 2020])
    
    def calcular_estatisticas(self, comarca, ano_selecionado):
        """
        Calcula estatísticas baseadas no fluxo anual acumulado.
        """
        if self.df.empty: return pd.DataFrame()

        # 1. Filtro base de Comarca
        df_c = self.df[self.df['comarca'] == comarca].copy()
        
        # Se não houver dados da comarca
        if df_c.empty: return pd.DataFrame()

        # 2. Filtrar janela confiável (a partir de 2020)
        START = pd.Timestamp('2020-01-01')
        df_f = df_c[df_c['data_distribuicao'] >= START].copy()
        
        if df_f.empty: return pd.DataFrame()

        # 3. Converter ano para período
        ano_periodo = pd.Period(str(ano_selecionado), freq='Y')

        # 4. Calcular fluxos acumulados até o ano de referência
        # Distribuídos acumulados até o ano
        distribuidos_acum = df_f[df_f['data_distribuicao'].dt.to_period('Y') <= ano_periodo]
        
        # Baixados acumulados até o ano
        baixados_acum = df_f[df_f['data_baixa'].dt.to_period('Y') <= ano_periodo]
        
        # 5. Agrupar por área e serventia
        grp_dist_acum = distribuidos_acum.groupby(['nome_area_acao', 'comarca']).size().rename('Distribuídos_acum')
        grp_baix_acum = baixados_acum.groupby(['nome_area_acao', 'comarca']).size().rename('Baixados_acum')
        
        # 6. Calcular fluxos do ano específico
        distribuidos_ano = df_f[df_f['data_distribuicao'].dt.to_period('Y') == ano_periodo]
        baixados_ano = df_f[df_f['data_baixa'].dt.to_period('Y') == ano_periodo]
        
        grp_dist_ano = distribuidos_ano.groupby(['nome_area_acao', 'comarca']).size().rename('Distribuídos')
        grp_baix_ano = baixados_ano.groupby(['nome_area_acao', 'comarca']).size().rename('Baixados')

        # 7. Consolidar todos os dados
        df_final = pd.concat([grp_dist_ano, grp_baix_ano, grp_dist_acum, grp_baix_acum], 
                            axis=1).fillna(0).astype(int).reset_index()

        # 8. Calcular pendentes no fim do ano
        df_final['Pendentes'] = (df_final['Distribuídos_acum'] - df_final['Baixados_acum']).clip(lower=0)

        # 9. Calcular Taxa de Congestionamento (fórmula: Pendentes / (Pendentes + Baixados_ano))
        denominador = df_final['Pendentes'] + df_final['Baixados']
        
        df_final['Taxa de Congestionamento (%)'] = np.where(
            denominador > 0,
            (df_final['Pendentes'] / denominador) * 100,
            0.0
        ).round(2)

        # 10. Selecionar colunas para apresentação
        df_final = df_final[['nome_area_acao', 'comarca',
                           'Distribuídos', 'Baixados', 'Pendentes',
                           'Taxa de Congestionamento (%)']]

        # 11. Linha de Totais
        totais = {
            'nome_area_acao': 'TOTAL',
            'comarca': '',
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
        Usa a lógica de fluxo anual acumulado.
        """
        if self.df.empty: return px.bar(title="Sem dados")

        # 1. Filtrar janela confiável
        START = pd.Timestamp('2020-01-01')
        df_f = self.df[self.df['data_distribuicao'] >= START].copy()
        
        if df_f.empty: return px.bar(title="Sem dados")

        # 2. Converter ano para período
        ano_periodo = pd.Period(str(ano_selecionado), freq='Y')

        # 3. Preparar dados agregados por Comarca e Área
        
        # Distribuídos acumulados até o ano
        dist_acum = df_f[df_f['data_distribuicao'].dt.to_period('Y') <= ano_periodo]
        dist_acum_group = dist_acum.groupby(['comarca', 'nome_area_acao']).size().rename('dist_acum')
        
        # Baixados acumulados até o ano
        baix_acum = df_f[df_f['data_baixa'].dt.to_period('Y') <= ano_periodo]
        baix_acum_group = baix_acum.groupby(['comarca', 'nome_area_acao']).size().rename('baix_acum')
        
        # Baixados no ano específico
        baix_ano = df_f[df_f['data_baixa'].dt.to_period('Y') == ano_periodo]
        baix_ano_group = baix_ano.groupby(['comarca', 'nome_area_acao']).size().rename('baixados')

        # 4. Merge e cálculo
        df_agg = pd.concat([dist_acum_group, baix_acum_group, baix_ano_group], axis=1).fillna(0)
        
        # Calcular pendentes
        df_agg['pendentes'] = (df_agg['dist_acum'] - df_agg['baix_acum']).clip(lower=0)
        
        # Calcular taxa de congestionamento
        denominador = df_agg['pendentes'] + df_agg['baixados']
        df_agg['taxa'] = np.where(
            denominador > 0,
            (df_agg['pendentes'] / denominador) * 100,
            0
        ).round(2)
        
        df_agg = df_agg.reset_index()

        # 5. Filtrar possíveis infinitos ou NaNs residuais
        df_agg = df_agg[df_agg['taxa'].notna()]

        # 6. Plot
        fig = px.bar(
            df_agg,
            x='comarca',
            y='taxa',
            color='nome_area_acao',
            barmode='group',
            title=f'Taxa de Congestionamento - {ano_selecionado} (Fluxo Acumulado)',
            text_auto='.2f',
            labels={'taxa': 'Taxa de Congestionamento (%)', 'nome_area_acao': 'Área', 'comarca': 'Comarca'}
        )
        
        fig.update_traces(textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', yaxis_range=[0, 110])
        
        return fig

    def plotar_graficos_comarca(self, comarca):
        """
        Gera gráfico de linha evolutivo usando a lógica de fluxo anual acumulado.
        """
        if self.df.empty: return px.line(title="Sem dados")

        comarca_norm = str(comarca).strip().lower()
        df_c = self.df[self.df['comarca'].str.strip().str.lower() == comarca_norm].copy()

        if df_c.empty:
            return px.line(title=f'Sem dados para a comarca: {comarca}')

        # 1. Filtrar janela confiável
        START = pd.Timestamp('2020-01-01')
        df_f = df_c[df_c['data_distribuicao'] >= START].copy()
        
        if df_f.empty:
            return px.line(title=f'Sem dados para a comarca: {comarca}')

        # 2. Determinar intervalo de anos para o gráfico
        min_ano = 2020
        max_ano = df_f['data_distribuicao'].dt.year.max()
        anos = list(range(min_ano, max_ano + 1))
        
        dados_grafico = []

        # 3. Áreas disponíveis nessa comarca
        areas = df_f['nome_area_acao'].unique()

        for area in areas:
            df_area = df_f[df_f['nome_area_acao'] == area]
            
            for ano in anos:
                ano_periodo = pd.Period(str(ano), freq='Y')
                
                # Fluxos acumulados até o ano
                dist_acum = len(df_area[df_area['data_distribuicao'].dt.to_period('Y') <= ano_periodo])
                baix_acum = len(df_area[df_area['data_baixa'].dt.to_period('Y') <= ano_periodo])
                
                # Baixados no ano específico
                baix_ano = len(df_area[df_area['data_baixa'].dt.to_period('Y') == ano_periodo])
                
                # Pendentes no fim do ano
                pendentes = max(dist_acum - baix_acum, 0)
                
                # Calcular taxa de congestionamento
                denominador = pendentes + baix_ano
                if denominador > 0:
                    taxa = (pendentes / denominador) * 100
                else:
                    taxa = 0.0
                
                # Só adiciona se houver algum movimento
                if pendentes > 0 or baix_ano > 0:
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
            labels={'ano': 'Ano', 'taxa': 'Taxa de Congestionamento (%)', 'nome_area_acao': 'Área de Ação'}
        )
        
        fig.update_layout(
            yaxis_range=[0, 105],
            xaxis=dict(tickmode='linear')
        )
        
        return fig
