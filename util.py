import numpy as np
import pandas as pd
import plotly.express as px

class ProcessosAnalisador:
    def __init__(self, arquivo_csv):
        # Carrega dados já agrupados
        self.df = self._carregar_dados(arquivo_csv)
        self._mapear_colunas()  # Mapeia as colunas disponíveis
    
    def _carregar_dados(self, arquivo_csv):
        """Carrega o CSV com dados já pré-calculados"""
        try:
            df = pd.read_csv(arquivo_csv, sep=',', encoding='utf-8')
            print(f"Arquivo carregado: {arquivo_csv}")
            print(f"Forma do dataframe: {df.shape}")
            print(f"Colunas disponíveis: {list(df.columns)}")
            print(f"\nPrimeiras linhas:\n{df.head()}")
            return df
        except Exception as e:
            print(f"Erro ao carregar CSV: {e}")
            return pd.DataFrame()
    
    def _mapear_colunas(self):
        """Mapeia as colunas específicas do seu CSV"""
        if self.df.empty:
            return
        
        # Mapeamento direto das colunas do seu CSV
        self.colunas = {
            'ano': 'ano_ref',  # ano_ref no seu CSV
            'comarca': 'comarca',  # comarca no seu CSV
            'nome_area_acao': 'nome_area_acao',  # nome_area_acao no seu CSV
            'distribuidos': 'Distribuidos_ano',  # Distribuidos_ano no seu CSV
            'baixados': 'Baixados_ano',  # Baixados_ano no seu CSV
            'pendentes': 'Pendentes_ano',  # Pendentes_ano no seu CSV
            'taxa_congestionamento': 'Taxa_Cong_anual (%)'  # Taxa_Cong_anual (%) no seu CSV
        }
        
        # Verificar se todas as colunas existem
        colunas_faltantes = []
        for col_nome, col_csv in self.colunas.items():
            if col_csv not in self.df.columns:
                colunas_faltantes.append(col_csv)
        
        if colunas_faltantes:
            print(f"Aviso: Colunas faltantes no CSV: {colunas_faltantes}")
        
        print(f"Colunas mapeadas: {self.colunas}")
    
    def obter_comarcas_disponiveis(self):
        if self.df.empty or 'comarca' not in self.df.columns: 
            return []
        
        comarcas = self.df['comarca'].dropna().unique()
        # Remover valores vazios e ordenar
        comarcas = [c for c in comarcas if str(c).strip() not in ['', 'nan']]
        return sorted(comarcas)
    
    def obter_anos_disponiveis(self):
        if self.df.empty or 'ano_ref' not in self.df.columns: 
            return []
        
        # Obter anos únicos da coluna ano_ref
        anos_series = self.df['ano_ref'].dropna()
        
        # Converter para inteiros
        anos = []
        for ano in anos_series.unique():
            try:
                ano_int = int(float(ano))  # Converte para float primeiro
                if ano_int >= 2020:  # Filtrar anos a partir de 2020
                    anos.append(ano_int)
            except (ValueError, TypeError):
                continue
        
        return sorted(set(anos))  # Remover duplicatas e ordenar
    
    def obter_dados_filtrados(self, comarca, ano_selecionado):
        """
        Retorna dados filtrados do CSV pré-calculado
        """
        if self.df.empty: 
            return pd.DataFrame()
        
        print(f"\nFiltrando: comarca='{comarca}', ano={ano_selecionado}")
        
        # Filtrar por comarca e ano
        try:
            # Converter para string para comparação
            ano_str = str(ano_selecionado)
            
            # Filtrar o dataframe
            mask = (
                (self.df['comarca'] == comarca) & 
                (self.df['ano_ref'].astype(str) == ano_str)
            )
            
            df_filtrado = self.df[mask].copy()
            
            print(f"Registros encontrados: {len(df_filtrado)}")
            
        except Exception as e:
            print(f"Erro ao filtrar dados: {e}")
            return pd.DataFrame()
        
        if df_filtrado.empty:
            print(f"Nenhum dado encontrado para {comarca} em {ano_selecionado}")
            return pd.DataFrame()
        
        # Criar dataframe de apresentação
        df_apresentacao = pd.DataFrame()
        
        # Mapear colunas do CSV para nomes de apresentação
        mapeamento_colunas = {
            'Área de Ação': 'nome_area_acao',
            'Comarca': 'comarca',
            'Distribuídos': 'Distribuidos_ano',
            'Baixados': 'Baixados_ano',
            'Pendentes': 'Pendentes_ano',
            'Taxa de Congestionamento (%)': 'Taxa_Cong_anual (%)'
        }
        
        # Adicionar apenas as colunas que existem
        for col_apresentacao, col_original in mapeamento_colunas.items():
            if col_original in df_filtrado.columns:
                df_apresentacao[col_apresentacao] = df_filtrado[col_original]
        
        # Se não encontrou nenhuma coluna
        if df_apresentacao.empty:
            print("Nenhuma coluna mapeada encontrada")
            # Usar todas as colunas disponíveis
            return df_filtrado
        
        # Ordenar por Área de Ação
        if 'Área de Ação' in df_apresentacao.columns:
            df_apresentacao = df_apresentacao.sort_values('Área de Ação')
        
        # Calcular linha de TOTAIS
        if not df_apresentacao.empty:
            totais = {
                'Área de Ação': 'TOTAL',
                'Comarca': ''
            }
            
            # Somar colunas numéricas
            colunas_numericas = ['Distribuídos', 'Baixados', 'Pendentes']
            for col in colunas_numericas:
                if col in df_apresentacao.columns:
                    try:
                        # Converter para numérico se necessário
                        df_apresentacao[col] = pd.to_numeric(df_apresentacao[col], errors='coerce')
                        totais[col] = df_apresentacao[col].sum()
                    except Exception as e:
                        print(f"Erro ao somar {col}: {e}")
                        totais[col] = 0
            
            # Calcular taxa de congestionamento total
            if 'Pendentes' in totais and 'Baixados' in totais:
                try:
                    pendentes = float(totais['Pendentes'])
                    baixados = float(totais['Baixados'])
                    denom_total = pendentes + baixados
                    if denom_total > 0:
                        taxa_total = (pendentes / denom_total) * 100
                        totais['Taxa de Congestionamento (%)'] = round(taxa_total, 2)
                    else:
                        totais['Taxa de Congestionamento (%)'] = 0.0
                except Exception as e:
                    print(f"Erro ao calcular taxa total: {e}")
                    totais['Taxa de Congestionamento (%)'] = 0.0
            
            # Adicionar linha de totais
            df_apresentacao = pd.concat([df_apresentacao, pd.DataFrame([totais])], ignore_index=True)
        
        print(f"Dataframe final para apresentação: {df_apresentacao.shape}")
        return df_apresentacao

    def plotar_graficos_comarca(self, comarca):
        """
        Gera gráfico de linha filtrado por áreas de ação específicas.
        """
        if self.df.empty: 
            return px.line(title="Sem dados disponíveis")
        
        # Lista de áreas permitidas (exatamente como no seu pedido)
        areas_desejadas = [
            'civel', 
            'criminal', 
            'infancia e juventude civel', 
            'infancia e juventude infracional', 
            'juizado especial civel', 
            'juizado especial criminal'
        ]
        
        try:
            # 1. Filtrar Comarca
            df_comarca = self.df[self.df['comarca'] == comarca].copy()
            
            # 2. Filtrar Áreas de Ação específicas
            # O .str.lower() ajuda a evitar erros de maiúsculas/minúsculas
            df_comarca = df_comarca[df_comarca['nome_area_acao'].str.lower().isin(areas_desejadas)]
            
        except Exception as e:
            print(f"Erro ao filtrar dados: {e}")
            return px.line(title=f"Erro ao filtrar dados: {comarca}")
        
        if df_comarca.empty:
            return px.line(title=f'Sem dados para as áreas selecionadas em: {comarca}')
        
        # Processar dados numéricos
        try:
            df_comarca['ano_ref'] = pd.to_numeric(df_comarca['ano_ref'], errors='coerce')
            df_comarca['Taxa_Cong_anual (%)'] = pd.to_numeric(df_comarca['Taxa_Cong_anual (%)'], errors='coerce')
            df_comarca = df_comarca.sort_values(['nome_area_acao', 'ano_ref'])
        except:
            return px.line(title=f'Erro ao processar dados para: {comarca}')
        
        # Criar gráfico
        try:
            fig = px.line(
                df_comarca,
                x='ano_ref',
                y='Taxa_Cong_anual (%)',
                color='nome_area_acao',
                markers=True,
                title=f'Taxa de Congestionamento por Ano - {comarca}',
                labels={
                    'ano_ref': 'Ano',
                    'Taxa_Cong_anual (%)': 'Taxa de Congestionamento (%)',
                    'nome_area_acao': 'Área de Ação'
                }
            )
            
            fig.update_layout(
                hovermode='closest',
                yaxis_range=[0, 105],
                xaxis=dict(tickmode='linear', dtick=1)
            )
            
            # Customização do Hover
            for trace in fig.data:
                area_name = trace.name
                area_data = df_comarca[df_comarca['nome_area_acao'] == area_name]
                
                hover_texts = []
                for _, row in area_data.iterrows():
                    text = f"<b>{area_name}</b><br>"
                    text += f"Ano: {int(row['ano_ref'])}<br>"
                    text += f"Taxa: {row['Taxa_Cong_anual (%)']:.2f}%<br>"
                    
                    # Campos opcionais
                    for campo, label in [('Distribuidos_ano', 'Distribuídos'), 
                                        ('Baixados_ano', 'Baixados'), 
                                        ('Pendentes_ano', 'Pendentes')]:
                        if campo in row:
                            text += f"{label}: {row[campo]:.0f}<br>"
                    
                    hover_texts.append(text)
                
                trace.text = hover_texts
                trace.hovertemplate = '%{text}<extra></extra>'
            
            return fig
            
        except Exception as e:
            print(f"Erro ao gerar gráfico: {e}")
            return px.line(title=f'Erro ao gerar gráfico')