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
        arquivo_csv = ('results_concat/tx_cong_anual.csv')
        df = pd.read_csv(arquivo_csv, sep=',', encoding='utf-8')

        # Renomear colunas se necessário para padronizar
        col_mapping = {
            'Comarca': 'comarca',
            'Área de Ação': 'nome_area_acao',
            'Ano': 'ano_ref',
            'Distribuídos': 'Distribuidos_ano',
            'Baixados': 'Baixados_ano',
            'Pendentes': 'Pendentes_ano',
            'Taxa de Congestionamento (%)': 'Taxa_Cong_anual (%)'    
        }

        for col_old, col_new in col_mapping.items():
            if col_old in df.columns:
                df = df.rename(columns={col_old: col_new})
        
        return df
    
    def obter_comarcas_disponiveis(self):
        if self.df.empty: return []
        return sorted(self.df['comarca'].dropna().unique())
    
    def obter_anos_disponiveis(self):
        if self.df.empty: return []
        # Considera anos disponíveis nos dados
        anos = self.df['ano'].dropna().unique()
        return sorted([int(x) for x in anos if x >= 2020])
    
    def obter_dados_filtrados(self, comarca, ano_selecionado):
        # Retorna dados filtrados do CSV pré-calculado
        if self.df.empty: 
            return pd.DataFrame()
        
        # Filtrar por comarca e ano
        df_filtrado = self.df[
            (self.df['comarca'] == comarca) & 
            (self.df['ano'] == ano_selecionado)
        ].copy()
        
        if df_filtrado.empty:
            return pd.DataFrame()
        
        # Selecionar e renomear colunas para apresentação
        cols_presentes = []
        colunas_desejadas = [
            'nome_area_acao', 'comarca',
            'Distribuidos_ano', 'Baixados_ano', 'Pendentes_ano', 'Taxa_Cong_anual (%)'
        ]
        
        for col in colunas_desejadas:
            if col in df_filtrado.columns:
                cols_presentes.append(col)
        
        df_filtrado = df_filtrado[cols_presentes]
        
        # Renomear colunas para apresentação
        cols_rename = {
            'nome_area_acao': 'Área de Ação',
            'comarca': 'Comarca',
            'Distribuidos_ano': 'Distribuídos',
            'Baixados_ano': 'Baixados',
            'Pendentes_ano': 'Pendentes',
            'Taxa_Cong_anual (%)': 'Taxa de Congestionamento (%)'
        }
        
        for col_old, col_new in cols_rename.items():
            if col_old in df_filtrado.columns:
                df_filtrado = df_filtrado.rename(columns={col_old: col_new})
        
        # Calcular totais
        if not df_filtrado.empty:
            totais = {}
            for col in ['Distribuídos', 'Baixados', 'Pendentes']:
                if col in df_filtrado.columns:
                    totais[col] = df_filtrado[col].sum()
            
            # Calcular taxa de congestionamento total
            if 'Pendentes' in totais and 'Baixados' in totais:
                denom_total = totais['Pendentes'] + totais['Baixados']
                if denom_total > 0:
                    totais['Taxa de Congestionamento (%)'] = round(
                        (totais['Pendentes'] / denom_total * 100), 2
                    )
                else:
                    totais['Taxa de Congestionamento (%)'] = 0.0
            
            totais['Área de Ação'] = 'TOTAL'
            totais['Comarca'] = ''
            
            # Adicionar linha de totais
            df_filtrado = pd.concat([df_filtrado, pd.DataFrame([totais])], ignore_index=True)
        
        return df_filtrado

    def plotar_graficos_comarca(self, comarca):
        """
        Gera gráfico de linha usando dados pré-calculados
        """
        if self.df.empty: 
            return px.line(title="Sem dados")
        
        # Filtrar dados da comarca
        df_comarca = self.df[self.df['comarca'] == comarca].copy()
        
        if df_comarca.empty:
            return px.line(title=f'Sem dados para a comarca: {comarca}')
        
        # Verificar se temos a coluna de taxa de congestionamento
        taxa_col = 'taxa_congestionamento'
        if taxa_col not in df_comarca.columns:
            # Tentar encontrar coluna similar
            for col in df_comarca.columns:
                if 'taxa' in col.lower() or 'congestionamento' in col.lower():
                    taxa_col = col
                    break
        
        # Verificar se temos dados suficientes
        if df_comarca['ano'].nunique() < 2:
            return px.line(title=f'Dados insuficientes para gráfico histórico: {comarca}')
        
        # Ordenar por ano
        df_comarca = df_comarca.sort_values('ano')
        
        # Criar gráfico de linha
        fig = px.line(
            df_comarca,
            x='ano',
            y=taxa_col,
            color='nome_area_acao',
            markers=True,
            title=f'Taxa de Congestionamento por Ano - {comarca}',
            labels={
                'ano': 'Ano',
                taxa_col: 'Taxa de Congestionamento (%)',
                'nome_area_acao': 'Área de Ação'
            }
        )
        
        fig.update_layout(
            yaxis_range=[0, 105],
            xaxis=dict(tickmode='linear'),
            hovermode='x unified'
        )
        
        return fig
