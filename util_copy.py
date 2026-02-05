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
            'serventia': 'serventia',  # serventia no seu CSV
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
            'Serventia': 'serventia',
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
        
        # Ordenar por Serventia
        if 'Serventia' in df_apresentacao.columns:
            df_apresentacao = df_apresentacao.sort_values('Serventia')
        
        # Calcular linha de TOTAIS
        if not df_apresentacao.empty:
            totais = {
                'Serventia': 'TOTAL',
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
        Gera gráfico de linha usando dados pré-calculados
        Versão simplificada com hover personalizado
        """
        if self.df.empty: 
            return px.line(title="Sem dados disponíveis")
        
        print(f"\nGerando gráfico para comarca: {comarca}")
        
        # Filtrar dados da comarca
        try:
            df_comarca = self.df[self.df['comarca'] == comarca].copy()
        except Exception as e:
            print(f"Erro ao filtrar comarca: {e}")
            return px.line(title=f"Erro ao filtrar comarca: {comarca}")
        
        if df_comarca.empty:
            return px.line(title=f'Sem dados para a comarca: {comarca}')
        
        # Processar dados
        try:
            df_comarca['ano_ref'] = pd.to_numeric(df_comarca['ano_ref'], errors='coerce')
            df_comarca['Taxa_Cong_anual (%)'] = pd.to_numeric(df_comarca['Taxa_Cong_anual (%)'], errors='coerce')
            df_comarca = df_comarca.sort_values('ano_ref')
        except:
            return px.line(title=f'Erro ao processar dados para: {comarca}')
        
        # Criar gráfico
        try:
            # Criar figura básica
            fig = px.line(
                df_comarca,
                x='ano_ref',
                y='Taxa_Cong_anual (%)',
                color='serventia',
                markers=True,
                title=f'Taxa de Congestionamento por Ano - {comarca}',
                labels={
                    'ano_ref': 'Ano',  # Eixo X agora mostra 'Ano'
                    'Taxa_Cong_anual (%)': 'Taxa de Congestionamento (%)',  # Eixo Y
                    'serventia': 'Serventia'  # Legenda agora mostra 'Serventia'
                }
            )
            
            # Configurar hover para mostrar apenas informações da linha específica
            fig.update_layout(
                hovermode='closest',  # Apenas mostra a linha mais próxima do cursor
                yaxis_range=[0, 105],
                xaxis=dict(tickmode='linear', dtick=1)
            )
            
            # Personalizar cada linha individualmente
            for trace in fig.data:
                # Obter o nome da área de ação desta linha
                serv_name = trace.name
                
                # Filtrar dados apenas para esta área
                serv_data = df_comarca[df_comarca['serventia'] == serv_name]
                
                # Criar texto do hover personalizado
                hover_texts = []
                for _, row in serv_data.sort_values('ano_ref').iterrows():
                    text = f"<b>{serv_name}</b><br>"
                    text += f"Ano: {int(row['ano_ref'])}<br>"
                    text += f"Taxa: {row['Taxa_Cong_anual (%)']:.2f}%<br>"
                    
                    # Adicionar dados adicionais se disponíveis
                    if 'Distribuidos_ano' in row:
                        text += f"Distribuídos: {row['Distribuidos_ano']:.0f}<br>"
                    if 'Baixados_ano' in row:
                        text += f"Baixados: {row['Baixados_ano']:.0f}<br>"
                    if 'Pendentes_ano' in row:
                        text += f"Pendentes: {row['Pendentes_ano']:.0f}<br>"
                    
                    hover_texts.append(text)
                
                # Atribuir os textos ao trace
                trace.text = hover_texts
                trace.hovertemplate = '%{text}<extra></extra>'
            
            return fig
            
        except Exception as e:
            print(f"Erro: {e}")
            return px.line(title=f'Erro ao gerar gráfico')