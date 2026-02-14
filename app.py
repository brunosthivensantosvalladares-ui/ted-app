import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime, time, timedelta
from io import BytesIO
from fpdf import FPDF
import time as time_module # Importado para evitar conflito com datetime.time

# --- CONFIGURAÇÕES DE MARCA ---
NOME_SISTEMA = "Up 2 Today"
SLOGAN = "Seu Controle. Nossa Prioridade."
LOGO_URL = "https://i.postimg.cc/85HwzdmP/logo-png.png"
ORDEM_AREAS = ["Motorista", "Borracharia", "Mecânica", "Elétrica", "Chapeamento", "Limpeza"]
LISTA_TURNOS = ["Não definido", "Dia", "Noite"]

# PALETA DE CORES EXTRAÍDA FIELMENTE DO LOGOTIPO U2T
COR_AZUL = "#1b224c" # Azul Marinho Profundo do 'U'
COR_VERDE = "#31ad64" # Verde Esmeralda do '2T'
COR_FUNDO = "#f4f7f6"
COR_DOURADO = "#FFD700" # Amarelo Dourado para Destaque

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title=f"{NOME_SISTEMA} - Tudo em Dia", layout="wide", page_icon="🛠️")

# --- CSS REVISADO: SETA CINZA, SIDEBAR #DFDFDF E DESTAQUE DE ABA ---
st.markdown(f"""
    <style>
    /* 1. FUNDOS: App Branco e Sidebar Cinza #DFDFDF */
    html, body, [data-testid="stAppViewContainer"], .stApp {{ background-color: #FFFFFF !important; }}
    [data-testid="stSidebar"] {{ background-color: #DFDFDF !important; }}

    /* 2. FLECHINHA DA SIDEBAR EM CINZA */
    [data-testid="stSidebarCollapsedControl"] svg, 
    button[data-testid="stBaseButton-headerNoPadding"] svg {{
        fill: #808080 !important;
        color: #808080 !important;
    }}

    /* 3. TEXTOS: Garante visibilidade em cinza escuro */
    p, label, span, div, .stMarkdown, [data-testid="stText"] {{
        color: #31333F !important;
    }}

    /* 4. CENTRALIZAÇÃO DOS BOTÕES DE LOGIN/CADASTRO */
    div[data-testid="stRadio"] > div {{
        display: flex;
        justify-content: center;
        background-color: #ffffff;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }}

    /* 5. BOTÕES GERAIS: Azul Marinho (Original) */
    button[kind="primary"], button[kind="secondary"], button {{
        background-color: #1b224c !important;
        border: 2px solid #31ad64 !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }}

    /* 5.1 BOTÃO DE RENOVAÇÃO (DOURADO) */
    div.stButton > button[key*="renov_btn"] {{
        background-color: {COR_DOURADO} !important;
        color: #000000 !important;
        border: 2px solid #B8860B !important;
        font-weight: bold !important;
    }}
    div.stButton > button[key*="renov_btn"] p {{ color: #000000 !important; }}

    /* 6. DESTAQUE DA ABA ATUAL: Verde Esmeralda */
    /* Aplica o verde apenas nos botões de navegação do topo que estão ativos */
    div.stHorizontalBlock button[kind="primary"] {{
        background-color: #31ad64 !important;
        border: 2px solid #1b224c !important;
    }}

    /* Texto branco em todos os botões */
    button p, button span, button div {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }}

    /* 7. ÍCONES: Olhinho e Calendário em Branco */
    button svg, [data-testid="stDateInput"] svg {{
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }}

    /* 8. CALENDÁRIO: Fundo Verde para Seleção */
    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [class*="Selected"],
    div[data-baseweb="calendar"] [class*="Highlighted"] {{
        background-color: #31ad64 !important;
        background: #31ad64 !important;
    }}

    /* 9. LOGOTIPO */
    .logo-u {{ color: #1b224c !important; }}
    .logo-2t {{ color: #31ad64 !important; }}
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÃO DO PAINEL DE PAGAMENTO PROFISSIONAL ---
def exibir_painel_pagamento_pro(origem):
    with st.container(border=True):
        st.markdown(f"""
            <div style='text-align: center; color: #31333F;'>
                <h2 style='color: {COR_AZUL};'>💼 Pacote Up 2 Today Pro</h2>
                <p style='font-size: 1.4rem; font-weight: bold; color: {COR_VERDE}; margin-bottom: 5px;'>R$ 299,00 / mês</p>
                <p style='font-style: italic; font-size: 0.9rem;'>Gestão completa para frotas que não podem parar.</p>
                <div style='text-align: left; background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 15px 0; border: 1px solid #ddd;'>
                    <p>✅ <b>Gestão Master:</b> Agenda e Cadastro de Manutenções ilimitados.</p>
                    <p>✅ <b>Equipe Total:</b> Acessos para motoristas e administradores sem limites.</p>
                    <p>✅ <b>Indicadores Inteligentes:</b> Gráficos de performance e Lead Time real.</p>
                    <p>✅ <b>Relatórios Ilimitados:</b> Exportação profissional em PDF e Excel.</p>
                </div>
                <p>Escaneie o QR Code abaixo no app do seu banco:</p>
            </div>
        """, unsafe_allow_html=True)
        _, col_qr, _ = st.columns([1, 1, 1])
        col_qr.image("https://i.postimg.cc/3Nn86MF0/QRcode.png", use_container_width=True)
        st.markdown("<p style='text-align: center;'><b>Chave Pix (Copie e Cole):</b></p>", unsafe_allow_html=True)
        st.code("3a7713a1-0a98-41b6-86b5-268c70cfe3f8")
        if st.button("❌ Minimizar detalhes", key=f"min_btn_{origem}"):
            st.session_state[f"show_pay_{origem}"] = False
            st.rerun()

# --- 2. FUNÇÕES DE SUPORTE E BANCO ---
@st.cache_resource
def get_engine():
    db_url = st.secrets.get("database_url") or os.environ.get("database_url", "postgresql://neondb_owner:npg_WRMhXvJVY79d@ep-lucky-sound-acy7xdyi-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require")
    return create_engine(db_url.replace("postgres://", "postgresql://", 1), pool_pre_ping=True)

def inicializar_banco():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS tarefas (id SERIAL PRIMARY KEY, data TEXT, executor TEXT, prefixo TEXT, inicio_disp TEXT, fim_disp TEXT, descricao TEXT, area TEXT, turno TEXT, realizado BOOLEAN DEFAULT FALSE, id_chamado INTEGER, origem TEXT, empresa_id TEXT)"))
            conn.execute(text("CREATE TABLE IF NOT EXISTS chamados (id SERIAL PRIMARY KEY, motorista TEXT, prefixo TEXT, descricao TEXT, data_solicitacao TEXT, status TEXT DEFAULT 'Pendente', empresa_id TEXT)"))
            # NOVA TABELA DE EMPRESAS PARA SAAS
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS empresa (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    data_cadastro DATE DEFAULT CURRENT_DATE,
                    status_assinatura TEXT DEFAULT 'trial',
                    data_expiracao DATE DEFAULT (CURRENT_DATE + INTERVAL '7 days')
                )
            """))
            # NOVA TABELA DE USUÁRIOS (MOTORISTAS/EQUIPE)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    login TEXT NOT NULL,
                    senha TEXT NOT NULL,
                    perfil TEXT DEFAULT 'motorista',
                    empresa_id TEXT NOT NULL,
                    UNIQUE(login, empresa_id)
                )
            """))
            try: conn.execute(text("ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS empresa_id TEXT DEFAULT 'U2T_MATRIZ'"))
            except: pass
            try: conn.execute(text("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS empresa_id TEXT DEFAULT 'U2T_MATRIZ'"))
            except: pass
            conn.commit()
    except: pass

def to_excel_native(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Manutencoes')
    return output.getvalue()

@st.cache_data(show_spinner=False)
def gerar_pdf_periodo(df_periodo, data_inicio, data_fim):
    pdf = FPDF()
    pdf.add_page()
    
    # --- CABEÇALHO COM MARCA U2T (AJUSTADO: LETRAS PRÓXIMAS) ---
    pdf.set_font("Arial", "B", 22)
    pdf.set_text_color(27, 34, 76) # Azul Logo
    pdf.cell(6, 10, "U", ln=0)     # Célula estreita para aproximar
    pdf.set_text_color(49, 173, 100) # Verde Logo
    pdf.cell(40, 10, "2T", ln=0)
    
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(144, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1, align="R")
    
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(27, 34, 76)
    pdf.cell(190, 10, f"RELATORIO DE MANUTENCAO - {NOME_SISTEMA.upper()}", ln=True, align="C")
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 8, f"Periodo: {data_inicio.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(5)
    
    for d_process in sorted(df_periodo['data'].unique(), reverse=True):
        d_formatada = pd.to_datetime(d_process).strftime('%d/%m/%Y')
        pdf.set_font("Arial", "B", 11); pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 8, f" DATA: {d_formatada}", ln=True, fill=True)
        
        for area in ORDEM_AREAS:
            df_area = df_periodo[(df_periodo['data'] == d_process) & (df_periodo['area'] == area)]
            if not df_area.empty:
                pdf.set_font("Arial", "B", 9); pdf.set_text_color(49, 173, 100)
                pdf.cell(190, 7, f" Setor: {area}", ln=True)
                
                # Títulos da Tabela (Restaurado para Cinza)
                pdf.set_font("Arial", "B", 8); pdf.set_text_color(50); pdf.set_fill_color(230, 230, 230)
                pdf.cell(20, 6, "Prefixo", 1, 0, 'C', True)
                pdf.cell(35, 6, "Executor", 1, 0, 'C', True)
                pdf.cell(40, 6, "Disponibilidade", 1, 0, 'C', True)
                pdf.cell(95, 6, "Descricao", 1, 1, 'C', True)
                
                # Linhas da Tabela
                pdf.set_font("Arial", "", 7); pdf.set_text_color(0)
                for _, row in df_area.iterrows():
                    pdf.cell(20, 6, str(row['prefixo']), 1, 0, 'C')
                    pdf.cell(35, 6, str(row['executor'])[:20], 1, 0, 'C')
                    pdf.cell(40, 6, f"{row['inicio_disp']} - {row['fim_disp']}", 1, 0, 'C')
                    pdf.cell(95, 6, str(row['descricao'])[:75], 1, 1, 'L')
                pdf.ln(2)
                
    return pdf.output(dest='S').encode('latin-1')

# --- 3. LÓGICA DE LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False
if "aba_login" not in st.session_state: st.session_state["aba_login"] = "Acessar"

if not st.session_state["logado"]:
    _, col_login, _ = st.columns([1.2, 1, 1.2])
    with col_login:
        placeholder_topo = st.empty()
        # Logotipo centralizado com cores travadas
        placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span class='logo-u'>U</span><span class='logo-2t'>2T</span></h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-style: italic; color: #555; margin-top: 0;'>{SLOGAN}</p>", unsafe_allow_html=True)
        
        # ALTERNÂNCIA ENTRE LOGIN E CADASTRO (Centralizado pelo CSS acima)
        aba = st.radio("Selecione uma opção", ["Acessar", "Criar Conta"], horizontal=True, label_visibility="collapsed")
        
        if aba == "Acessar":
            with st.container(border=True):
                user_input = st.text_input("E-mail ou Usuário", key="u_log").lower()
                pw_input = st.text_input("Senha", type="password", key="p_log")
                if st.button(f"Acessar Painel {NOME_SISTEMA}", use_container_width=True, type="primary"):
                    engine = get_engine()
                    inicializar_banco()
                    
                    # 1. VERIFICAÇÃO DE USUÁRIOS MASTER (ESTÁTICOS)
                    masters = {
                        "bruno": {"pw": "master789", "perfil": "admin", "empresa": "U2T_MATRIZ", "login_original": "bruno"},
                        "motorista": {"pw": "12345", "perfil": "motorista", "empresa": "U2T_MATRIZ", "login_original": "motorista_padrao"}
                    }
                    
                    logado_agora = False
                    if user_input in masters and masters[user_input]["pw"] == pw_input:
                        st.session_state.update({"logado": True, "perfil": masters[user_input]["perfil"], "empresa": masters[user_input]["empresa"], "usuario_ativo": masters[user_input]["login_original"]})
                        logado_agora = True
                    else:
                        # 2. VERIFICAÇÃO NO BANCO DE DADOS (CLIENTES SAAS - AGORA ACEITA E-MAIL OU NOME)
                        with engine.connect() as conn:
                            res = conn.execute(text("""
                                SELECT nome, email, senha, data_expiracao, status_assinatura 
                                FROM empresa 
                                WHERE LOWER(email) = :u OR LOWER(nome) = :u
                            """), {"u": user_input}).fetchone()
                            
                            if res and res[2] == pw_input:
                                hoje = datetime.now().date()
                                # TRAVA DE SEGURANÇA: DATA DE EXPIRAÇÃO COM BOTÃO DE RENOVAÇÃO
                                if res[3] < hoje and res[4] != 'ativo':
                                    st.error(f"⚠️ Acesso bloqueado: Período de teste expirado em {res[3].strftime('%d/%m/%Y')}.")
                                    if st.button("Renove agora a sua assinatura", use_container_width=True, type="primary", key="renov_btn_login"):
                                        st.session_state["show_pay_login"] = True
                                    if st.session_state.get("show_pay_login"):
                                        exibir_painel_pagamento_pro()
                                else:
                                    st.session_state.update({"logado": True, "perfil": "admin", "empresa": res[0], "usuario_ativo": res[0]})
                                    logado_agora = True
                            else:
                                # 3. VERIFICAÇÃO DE USUÁRIOS DA EQUIPE (MOTORISTAS OU OUTROS ADMINS SECUNDÁRIOS)
                                u_equipe = conn.execute(text("""
                                    SELECT login, senha, perfil, empresa_id FROM usuarios WHERE LOWER(login) = :u
                                """), {"u": user_input}).fetchone()
                                if u_equipe and u_equipe[1] == pw_input:
                                    st.session_state.update({"logado": True, "perfil": u_equipe[2], "empresa": u_equipe[3], "usuario_ativo": u_equipe[0]})
                                    logado_agora = True
                                    
                    if logado_agora:
                        if "opcao_selecionada" in st.session_state: del st.session_state["opcao_selecionada"]
                        with st.spinner(""):
                            for t in ["UP", "UP 2", "UP 2 T", "UP 2 TODAY"]:
                                placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span class='logo-u'>{t[:2]}</span><span class='logo-2t'>{t[2:]}</span></h1>", unsafe_allow_html=True)
                                time_module.sleep(0.05)
                        st.rerun()
                    else:
                        # Só mostra erro se não for o caso de bloqueio por expiração já tratado acima
                        try: expirou = res[3] < hoje and res[4] != 'ativo'
                        except: expirou = False
                        if not expirou: st.error("Dados incorretos ou conta inexistente.")

        else: # ABA CRIAR CONTA
            with st.container(border=True):
                st.markdown(f"<h4 style='color:{COR_AZUL}'>🚀 7 Dias Grátis</h4>", unsafe_allow_html=True)
                n_emp = st.text_input("Nome da Empresa")
                n_ema = st.text_input("E-mail Corporativo")
                n_sen = st.text_input("Senha", type="password")
                if st.button("Criar minha conta agora", use_container_width=True, type="primary"):
                    if n_emp and n_ema and n_sen:
                        try:
                            engine = get_engine()
                            inicializar_banco()
                            expira = datetime.now().date() + timedelta(days=7)
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO empresa (nome, email, senha, data_expiracao) VALUES (:n, :e, :s, :d)"), {"n": n_emp, "e": n_ema, "s": n_sen, "d": expira})
                                conn.commit()
                            st.success("✅ Conta criada! Agora faça login na aba 'Acessar'.")
                        except Exception as e:
                            st.error("Este e-mail já está cadastrado.")
                    else: st.warning("Preencha todos os campos.")

else:
    engine = get_engine(); inicializar_banco()
    emp_id = st.session_state["empresa"] # Filtro global
    usuario_ativo = st.session_state.get("usuario_ativo", "")

    # --- BANNER DE PAGAMENTO PROFISSIONAL ANTECIPADO (2 DIAS ANTES) ---
    if st.session_state["perfil"] == "admin" and usuario_ativo != "bruno":
        with engine.connect() as conn:
            dados_exp = conn.execute(text("SELECT data_expiracao, status_assinatura FROM empresa WHERE nome = :n"), {"n": emp_id}).fetchone()
        if dados_exp and dados_exp[1] == 'trial':
            hoje_dt = datetime.now().date()
            data_exp_dt = pd.to_datetime(dados_exp[0]).date()
            dias_rest = (data_exp_dt - hoje_dt).days
            if 0 <= dias_rest <= 2:
                with st.warning(f"📢 **Atenção:** Seu período de teste termina em {dias_rest} dias ({data_exp_dt.strftime('%d/%m/%Y')}). Antecipe o pagamento para evitar bloqueios!"):
                    if st.button("Renove agora a sua assinatura", key="renov_btn_banner", type="primary"):
                        st.session_state["show_pay_banner"] = True
                    if st.session_state.get("show_pay_banner"):
                        exibir_painel_pagamento_pro()
    
    if st.session_state["perfil"] == "motorista":
        opcoes = ["✍️ Abrir Solicitação", "📜 Status"]
    else:
        opcoes = ["📅 Agenda Principal", "📋 Cadastro Direto", "📥 Chamados Oficina", "📊 Indicadores", "👥 Minha Equipe"]
        # ADICIONA ABA MASTER APENAS PARA O BRUNO
        if usuario_ativo == "bruno":
            opcoes.append("👑 Gestão Master")

    if "opcao_selecionada" not in st.session_state or st.session_state.opcao_selecionada not in opcoes:
        st.session_state.opcao_selecionada = opcoes[0]
    
    if "radio_key" not in st.session_state:
        st.session_state.radio_key = 0

    def set_nav(target):
        st.session_state.opcao_selecionada = target
        st.session_state.radio_key += 1 

    # 1. BARRA LATERAL
    with st.sidebar:
        # LOGO DIMINUÍDO NA SIDEBAR
        _, col_img, _ = st.columns([0.15, 0.7, 0.15])
        with col_img:
            st.image(LOGO_URL, width=150)
        st.markdown(f"<p style='text-align: center; font-size: 0.8rem; color: #666; margin-top: -10px;'>{SLOGAN}</p>", unsafe_allow_html=True)
        st.divider()
        
        try:
            idx_seguro = opcoes.index(st.session_state.opcao_selecionada)
        except ValueError:
            idx_seguro = 0; st.session_state.opcao_selecionada = opcoes[0]

        escolha_sidebar = st.radio(
            "NAVEGAÇÃO", 
            opcoes, 
            index=idx_seguro,
            key=f"radio_nav_{st.session_state.radio_key}",
            on_change=lambda: st.session_state.update({"opcao_selecionada": st.session_state[f"radio_nav_{st.session_state.radio_key}"]})
        )
        
        st.divider()
        st.write(f"🏢 **Empresa:** {emp_id}")
        st.write(f"👤 **{st.session_state['perfil'].capitalize()}**")
        if st.button("Sair da Conta", type="primary"): 
            st.session_state["logado"] = False
            st.rerun()

    # 2. BOTÕES DE ABA NO TOPO
    cols = st.columns(len(opcoes))
    for i, nome in enumerate(opcoes):
        eh_ativo = nome == st.session_state.opcao_selecionada
        if cols[i].button(nome, key=f"btn_tab_{i}", use_container_width=True, 
                         type="primary" if eh_ativo else "secondary",
                         on_click=set_nav, args=(nome,)):
            pass

    st.divider()
    aba_ativa = st.session_state.opcao_selecionada

    # --- 3. CONTEÚDO DAS PÁGINAS ---
    if aba_ativa == "👑 Gestão Master" and usuario_ativo == "bruno":
        st.subheader("👑 Painel de Controle Master")
        st.info("💡 Bruno, aqui você ativa os pagamentos e define os prazos das empresas.")
        df_empresas = pd.read_sql(text("SELECT id, nome, email, data_cadastro, data_expiracao, status_assinatura FROM empresa ORDER BY id DESC"), engine)
        if not df_empresas.empty:
            for _, row in df_empresas.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1])
                    c1.write(f"**Empresa:** {row['nome']}\n\n**Email:** {row['email']}")
                    c2.write(f"📅 Cadastro: {row['data_cadastro']}\n\n⌛ Expira: {row['data_expiracao']}")
                    status_cor = "green" if row['status_assinatura'] == 'ativo' else "orange"
                    c3.markdown(f"Status: :{status_cor}[{row['status_assinatura'].upper()}]")
                    if row['status_assinatura'] != 'ativo':
                        if c4.button("✅ Ativar", key=f"ativar_{row['id']}", use_container_width=True):
                            with engine.connect() as conn:
                                conn.execute(text("UPDATE empresa SET status_assinatura = 'ativo', data_expiracao = :d WHERE id = :i"), {"d": datetime.now().date() + timedelta(days=365), "i": row['id']})
                                conn.commit()
                            st.rerun()
                    else:
                        if c4.button("🚫 Bloquear", key=f"bloq_{row['id']}", use_container_width=True):
                            with engine.connect() as conn:
                                conn.execute(text("UPDATE empresa SET status_assinatura = 'expirado' WHERE id = :i"), {"i": row['id']})
                                conn.commit()
                            st.rerun()

    elif aba_ativa == "✍️ Abrir Solicitação":
        st.subheader("✍️ Nova Solicitação de Manutenção")
        st.info("💡 **Dica:** Informe o prefixo e detalhe o problema para que a oficina possa se programar.")
        with st.form("f_ch", clear_on_submit=True):
            p, d = st.text_input("Prefixo do Veículo"), st.text_area("Descrição do Problema")
            if st.form_submit_button("Enviar para Oficina"):
                if p and d:
                    nome_motorista = st.session_state.get("usuario_ativo", "Motorista")
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO chamados (motorista, prefixo, descricao, data_solicitacao, status, empresa_id) VALUES (:m, :p, :d, :dt, 'Pendente', :eid)"), {"m": nome_motorista, "p": p, "d": d, "dt": str(datetime.now().date()), "eid": emp_id})
                        conn.commit()
                        st.success("✅ Solicitação enviada com sucesso! Acompanhe o status na aba ao lado.")

    elif aba_ativa == "📜 Status":
        st.subheader("📜 Status dos Meus Veículos")
        st.info("Aqui você pode ver se o seu veículo já foi agendado ou concluído pela oficina.")
        df_status = pd.read_sql(text("SELECT prefixo, data_solicitacao as data, status, descricao FROM chamados WHERE empresa_id = :eid ORDER BY id DESC"), engine, params={"eid": emp_id})
        st.dataframe(df_status, use_container_width=True, hide_index=True)

    elif aba_ativa == "📅 Agenda Principal":
        st.subheader("📅 Agenda Principal")
        try:
            df_stats = pd.read_sql(text("SELECT data, realizado FROM tarefas WHERE empresa_id = :eid"), engine, params={"eid": emp_id})
            if not df_stats.empty:
                df_stats['data'] = pd.to_datetime(df_stats['data']).dt.date
                hoje_dt = datetime.now().date()
                df_hoje = df_stats[df_stats['data'] == hoje_dt]
                m1, m2, m3 = st.columns(3)
                with m1: st.metric("Agendados Hoje", len(df_hoje))
                with m2: st.metric("Concluídos", len(df_hoje[df_hoje['realizado'] == True]))
                with m3: st.metric("Pendentes", len(df_hoje[df_hoje['realizado'] == False]))
                st.divider()
        except:
            st.warning("⚠️ O banco de dados está iniciando. Aguarde alguns segundos.")
            st.stop()
        st.info("✍️ **Logística:** Clique nas colunas de **Início** ou **Fim** para preencher. **PCM:** Clique em **Área** ou **Executor** para definir. O salvamento é automático.")
        df_a = pd.read_sql(text("SELECT * FROM tarefas WHERE empresa_id = :eid ORDER BY data DESC"), engine, params={"eid": emp_id})
        p_sel = st.date_input("Filtrar Período", [datetime.now().date(), datetime.now().date() + timedelta(days=1)], key="dt_filter")
        if not df_a.empty and len(p_sel) == 2:
            df_a['data'] = pd.to_datetime(df_a['data']).dt.date
            df_f = df_a[(df_a['data'] >= p_sel[0]) & (df_a['data'] <= p_sel[1])].copy()
            for d in sorted(df_f['data'].unique(), reverse=True):
                st.markdown(f"#### 🗓️ {d.strftime('%d/%m/%Y')}")
                for area in ORDEM_AREAS:
                    df_area_f = df_f[(df_f['data'] == d) & (df_f['area'] == area)].sort_values(by='id')
                    if not df_area_f.empty:
                        st.markdown(f"<p class='area-header'>📍 {area}</p>", unsafe_allow_html=True)
                        df_editor_base = df_area_f.set_index('id')
                        edited_df = st.data_editor(df_editor_base[['realizado', 'area', 'turno', 'prefixo', 'inicio_disp', 'fim_disp', 'executor', 'descricao', 'id_chamado']], 
                            column_config={"realizado": st.column_config.CheckboxColumn("OK", width="small"), "area": st.column_config.SelectboxColumn("Área", options=ORDEM_AREAS), "turno": st.column_config.SelectboxColumn("Turno", options=LISTA_TURNOS), "inicio_disp": st.column_config.TextColumn("Início (Preencher)"), "fim_disp": st.column_config.TextColumn("Fim (Preencher)"), "executor": st.column_config.TextColumn("Executor"), "id_chamado": None}, 
                            hide_index=False, use_container_width=True, key=f"ed_ted_{d}_{area}")
                        if not edited_df.equals(df_editor_base[['realizado', 'area', 'turno', 'prefixo', 'inicio_disp', 'fim_disp', 'executor', 'descricao', 'id_chamado']]):
                            with engine.connect() as conn:
                                for row_id, row in edited_df.iterrows():
                                    conn.execute(text("UPDATE tarefas SET realizado = :r, area = :ar, turno = :t, prefixo = :p, inicio_disp = :i, fim_disp = :f, executor = :ex, descricao = :ds WHERE id = :id"), {"r": bool(row['realizado']), "ar": str(row['area']), "t": str(row['turno']), "p": str(row['prefixo']), "i": str(row['inicio_disp']), "f": str(row['fim_disp']), "ex": str(row['executor']), "ds": str(row['descricao']), "id": int(row_id)})
                                    if row['realizado'] and pd.notnull(row['id_chamado']):
                                        try: conn.execute(text("UPDATE chamados SET status = 'Concluído' WHERE id = :ic"), {"ic": int(row['id_chamado'])})
                                        except: pass
                                conn.commit()
                                st.toast("Alteração salva!", icon="✅")
                                time_module.sleep(0.5); st.rerun()

    elif aba_ativa == "📋 Cadastro Direto":
        st.subheader("📝 Agendamento Direto")
        with st.form("f_d", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: d_i = st.date_input("Data", datetime.now()); e_i = c2.text_input("Executor"); p_i = c3.text_input("Prefixo"); a_i = c4.selectbox("Área", ORDEM_AREAS)
            ds_i, t_i = st.text_area("Descrição"), st.selectbox("Turno", LISTA_TURNOS)
            if st.form_submit_button("Confirmar Agendamento"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, descricao, area, turno, origem, empresa_id) VALUES (:dt, :ex, :pr, :ds, :ar, :tu, 'Direto', :eid)"), {"dt": str(d_i), "ex": e_i, "pr": p_i, "ds": ds_i, "ar": a_i, "tu": t_i, "eid": emp_id})
                    conn.commit(); st.success("✅ Serviço cadastrado!"); st.rerun()
        st.divider(); st.subheader("📋 Lista de serviços")
        df_lista = pd.read_sql(text("SELECT * FROM tarefas WHERE empresa_id = :eid ORDER BY data DESC, id DESC"), engine, params={"eid": emp_id})
        if not df_lista.empty:
            df_lista['data'] = pd.to_datetime(df_lista['data']).dt.date; df_lista['Exc'] = False
            ed_l = st.data_editor(df_lista[['Exc', 'data', 'turno', 'executor', 'prefixo', 'inicio_disp', 'fim_disp', 'descricao', 'area', 'id']], hide_index=True, use_container_width=True, key="ed_lista")
            if st.button("🗑️ Excluir Selecionados"):
                with engine.connect() as conn:
                    for i in ed_l[ed_l['Exc']==True]['id'].tolist(): conn.execute(text("DELETE FROM tarefas WHERE id = :id"), {"id": int(i)})
                    conn.commit(); st.warning("🗑️ Itens excluídos."); st.rerun()
            if st.session_state.ed_lista["edited_rows"]:
                with engine.connect() as conn:
                    for idx, changes in st.session_state.ed_lista["edited_rows"].items():
                        rid = int(df_lista.iloc[idx]['id'])
                        for col, val in changes.items():
                            if col != 'Exc': conn.execute(text(f"UPDATE tarefas SET {col} = :v WHERE id = :i"), {"v": str(val), "i": rid})
                    conn.commit(); st.rerun()

    elif aba_ativa == "📥 Chamados Oficina":
        st.subheader("📥 Chamados Oficina")
        df_p = pd.read_sql(text("SELECT id, motorista, prefixo, descricao FROM chamados WHERE status = 'Pendente' AND empresa_id = :eid"), engine, params={"eid": emp_id})
        if not df_p.empty: st.data_editor(df_p, use_container_width=True, hide_index=True)
        else: st.info("Nenhum chamado pendente.")

    elif aba_ativa == "📊 Indicadores":
        st.subheader("📊 Indicadores")
        df_ind = pd.read_sql(text("SELECT area, realizado FROM tarefas WHERE empresa_id = :eid"), engine, params={"eid": emp_id})
        if not df_ind.empty:
            st.bar_chart(df_ind['area'].value_counts())

    elif aba_ativa == "👥 Minha Equipe":
        st.subheader("👥 Gestão de Equipe e Acessos")
        with st.expander("➕ Cadastrar Novo Integrante", expanded=True):
            with st.form("form_novo_usuario", clear_on_submit=True):
                col1, col2, col3 = st.columns([1, 1, 1]); novo_u = col1.text_input("Login (Ex: pedro.motorista)"); nova_s = col2.text_input("Senha de Acesso", type="password"); novo_p = col3.selectbox("Cargo/Perfil", ["motorista", "admin"])
                if st.form_submit_button("Criar Acesso"):
                    if novo_u and nova_s:
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO usuarios (login, senha, perfil, empresa_id) VALUES (:u, :s, :p, :eid)"), {"u": novo_u.lower(), "s": nova_s, "p": novo_p, "eid": emp_id})
                                conn.commit(); st.success(f"✅ Acesso para '{novo_u}' ({novo_p}) criado!"); time_module.sleep(1.5); st.rerun()
                        except: st.error("Erro: Login já existe.")
                    else: st.warning("Preencha tudo.")
        st.divider(); st.subheader("Integrantes Cadastrados")
        df_users = pd.read_sql(text("SELECT id, login, senha, perfil as cargo FROM usuarios WHERE empresa_id = :eid"), engine, params={"eid": emp_id})
        if not df_users.empty:
            df_users['Exc'] = False
            ed_users = st.data_editor(df_users[['Exc', 'login', 'senha', 'cargo', 'id']], hide_index=True, use_container_width=True, column_config={"id": None, "Exc": st.column_config.CheckboxColumn("Excluir", width="small"), "cargo": st.column_config.SelectboxColumn("Cargo", options=["motorista", "admin"])}, key="editor_equipe")
            if st.button("🗑️ Excluir Selecionados da Equipe"):
                usuarios_para_deletar = ed_users[ed_users['Exc'] == True]['id'].tolist()
                if usuarios_para_deletar:
                    with engine.connect() as conn:
                        for u_id in usuarios_para_deletar: conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": int(u_id)})
                        conn.commit(); st.warning("Integrantes removidos."); time_module.sleep(1); st.rerun()
            if st.session_state.editor_equipe["edited_rows"]:
                with engine.connect() as conn:
                    for idx, changes in st.session_state.editor_equipe["edited_rows"].items():
                        user_db_id = int(df_users.iloc[idx]['id'])
                        for col, val in changes.items():
                            if col != 'Exc': conn.execute(text(f"UPDATE usuarios SET {col} = :v WHERE id = :i"), {"v": str(val), "i": user_db_id})
                    conn.commit(); st.toast("Equipe atualizada!", icon="👥")
        else: st.write("Nenhum integrante cadastrado.")
