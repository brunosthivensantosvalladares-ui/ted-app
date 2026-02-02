import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime, time, timedelta
from io import BytesIO
from fpdf import FPDF

# --- CONFIGURAÇÕES DE MARCA ---
NOME_SISTEMA = "Ted"
SLOGAN = "Seu Controle. Nossa Prioridade."
LOGO_URL = "https://i.postimg.cc/wTbmmT7r/logo-png.png"
ORDEM_AREAS = ["Motorista", "Borracharia", "Mecânica", "Elétrica", "Chapeamento", "Limpeza"]
LISTA_TURNOS = ["Não definido", "Dia", "Noite"]
COR_AZUL, COR_VERDE = "#3282b8", "#8ac926"

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title=f"{NOME_SISTEMA} - Tudo em Dia", layout="wide", page_icon="🛠️")

# --- CSS PARA UNIDADE VISUAL ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fa; }}
    /* Botão Primário (Azul Ted) */
    .stButton>button[kind="primary"] {{ background-color: {COR_AZUL}; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%; }}
    /* Botão Secundário (Inativo) */
    .stButton>button[kind="secondary"] {{ background-color: #e0e0e0; color: #333; border-radius: 8px; border: none; width: 100%; }}
    
    [data-testid="stSidebar"] {{ background-color: #ffffff; border-right: 1px solid #e0e0e0; }}
    .area-header {{ color: {COR_VERDE}; font-weight: bold; font-size: 1.1rem; border-left: 5px solid {COR_AZUL}; padding-left: 10px; margin-top: 20px; }}
    div[data-testid="stRadio"] > div {{ background-color: #f1f3f5; padding: 10px; border-radius: 10px; }}
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE E BANCO ---
@st.cache_resource
def get_engine():
    db_url = os.environ.get("database_url", "postgresql://neondb_owner:npg_WRMhXvJVY79d@ep-lucky-sound-acy7xdyi-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require")
    return create_engine(db_url.replace("postgres://", "postgresql://", 1), pool_pre_ping=True)

def inicializar_banco():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS tarefas (id SERIAL PRIMARY KEY, data TEXT, executor TEXT, prefixo TEXT, inicio_disp TEXT, fim_disp TEXT, descricao TEXT, area TEXT, turno TEXT, realizado BOOLEAN DEFAULT FALSE, id_chamado INTEGER, origem TEXT)"))
            conn.execute(text("CREATE TABLE IF NOT EXISTS chamados (id SERIAL PRIMARY KEY, motorista TEXT, prefixo TEXT, descricao TEXT, data_solicitacao TEXT, status TEXT DEFAULT 'Pendente')"))
            try: conn.execute(text("ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS origem TEXT"))
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
    pdf.set_font("Arial", "B", 16); pdf.set_text_color(50, 130, 184)
    pdf.cell(190, 10, f"Relatorio de Manutencao - {NOME_SISTEMA}", ln=True, align="C")
    pdf.set_font("Arial", "", 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 10, f"Periodo: {data_inicio.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(5)
    for d_process in sorted(df_periodo['data'].unique(), reverse=True):
        d_formatada = pd.to_datetime(d_process).strftime('%d/%m/%Y')
        pdf.set_font("Arial", "B", 14); pdf.cell(190, 10, f"Data: {d_formatada}", ln=True)
        for area in ORDEM_AREAS:
            df_area = df_periodo[(df_periodo['data'] == d_process) & (df_periodo['area'] == area)]
            if not df_area.empty:
                pdf.set_font("Arial", "B", 11); pdf.set_fill_color(230, 230, 230)
                pdf.cell(190, 7, f" Area: {area}", ln=True, fill=True)
                for _, row in df_area.iterrows():
                    pdf.set_font("Arial", "", 8); pdf.cell(190, 6, f"{row['prefixo']} | {row['executor']} | {str(row['descricao'])[:80]}", ln=True)
                pdf.ln(3)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. LÓGICA DE LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False

if not st.session_state["logado"]:
    _, col_login, _ = st.columns([1.2, 1, 1.2])
    with col_login:
        placeholder_topo = st.empty()
        placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span style='color: {COR_AZUL};'>T</span><span style='color: {COR_VERDE};'>ed</span></h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-style: italic; color: #555; margin-top: 0;'>{SLOGAN}</p>", unsafe_allow_html=True)
        with st.container(border=True):
            user = st.text_input("Usuário", key="u_log").lower()
            pw = st.text_input("Senha", type="password", key="p_log")
            if st.button("Acessar Painel Ted", use_container_width=True, type="primary"):
                users = {"bruno": "master789", "admin": "12345", "motorista": "12345"}
                if user in users and users[user] == pw:
                    # Resetar navegação ao logar para evitar erro de index
                    if "opcao_selecionada" in st.session_state: del st.session_state["opcao_selecionada"]
                    
                    import time
                    with st.spinner(""):
                        for t in ["Tu", "Tud", "Tudo ", "Tudo e", "Tudo em d", "Tudo em dia"]:
                            placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span style='color: {COR_AZUL};'>{t[:4]}</span><span style='color: {COR_VERDE};'>{t[4:]}</span></h1>", unsafe_allow_html=True)
                            time.sleep(0.05)
                    st.session_state["logado"], st.session_state["perfil"] = True, ("admin" if user != "motorista" else "motorista")
                    st.rerun()
                else: st.error("Usuário ou senha incorretos")
else:
    engine = get_engine(); inicializar_banco()
    
    # Define as opções por perfil
    if st.session_state["perfil"] == "motorista":
        opcoes = ["✍️ Abrir Solicitação", "📜 Status"]
    else:
        opcoes = ["📅 Agenda Principal", "📋 Cadastro Direto", "📥 Chamados Oficina", "📊 Indicadores"]

    # --- PROTEÇÃO CONTRA O ERRO DE INDEX (VALUEERROR) ---
    if "opcao_selecionada" not in st.session_state or st.session_state.opcao_selecionada not in opcoes:
        st.session_state.opcao_selecionada = opcoes[0]
    
    if "radio_key" not in st.session_state:
        st.session_state.radio_key = 0

    def set_nav(target):
        st.session_state.opcao_selecionada = target
        st.session_state.radio_key += 1 

    # 1. BARRA LATERAL
    with st.sidebar:
        st.image(LOGO_URL, use_container_width=True)
        st.markdown(f"<p style='text-align: center; font-size: 0.8rem; color: #666; margin-top: -10px;'>{SLOGAN}</p>", unsafe_allow_html=True)
        st.divider()
        
        # O rádio lateral com índice protegido
        try:
            idx_seguro = opcoes.index(st.session_state.opcao_selecionada)
        except ValueError:
            idx_seguro = 0
            st.session_state.opcao_selecionada = opcoes[0]

        escolha_sidebar = st.radio(
            "NAVEGAÇÃO", 
            opcoes, 
            index=idx_seguro,
            key=f"radio_nav_{st.session_state.radio_key}",
            on_change=lambda: st.session_state.update({"opcao_selecionada": st.session_state[f"radio_nav_{st.session_state.radio_key}"]})
        )
        
        st.divider()
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
    if aba_ativa == "✍️ Abrir Solicitação":
        st.subheader("✍️ Nova Solicitação de Manutenção")
        st.info("💡 **Dica:** Informe o prefixo e detalhe o problema para que a oficina possa se programar.")
        with st.form("f_ch", clear_on_submit=True):
            p, d = st.text_input("Prefixo do Veículo"), st.text_area("Descrição do Problema")
            if st.form_submit_button("Enviar para Oficina"):
                if p and d:
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO chamados (motorista, prefixo, descricao, data_solicitacao, status) VALUES ('motorista', :p, :d, :dt, 'Pendente')"), {"p": p, "d": d, "dt": str(datetime.now().date())})
                        conn.commit()
                    st.success("✅ Solicitação enviada com sucesso! Acompanhe o status na aba ao lado.")

    elif aba_ativa == "📜 Status":
        st.subheader("📜 Status dos Meus Veículos")
        st.info("Aqui você pode ver se o seu veículo já foi agendado ou concluído pela oficina.")
        df_status = pd.read_sql("SELECT prefixo, data_solicitacao as data, status, descricao FROM chamados ORDER BY id DESC", engine)
        st.dataframe(df_status, use_container_width=True, hide_index=True)

    elif aba_ativa == "📅 Agenda Principal":
        st.subheader("📅 Agenda Principal")
        st.info("💡 **Aviso:** Marque o campo 'OK' e clique em 'Salvar Tudo' para concluir os serviços.")
        df_a = pd.read_sql("SELECT * FROM tarefas ORDER BY data DESC", engine)
        hoje, amanha = datetime.now().date(), datetime.now().date() + timedelta(days=1)
        c_per, c_pdf, c_xls = st.columns([0.6, 0.2, 0.2])
        with c_per: p_sel = st.date_input("Filtrar Período", [hoje, amanha], key="dt_filter")
        if not df_a.empty and len(p_sel) == 2:
            df_a['data'] = pd.to_datetime(df_a['data']).dt.date
            df_f = df_a[(df_a['data'] >= p_sel[0]) & (df_a['data'] <= p_sel[1])]
            with c_pdf: st.download_button("📥 PDF", gerar_pdf_periodo(df_f, p_sel[0], p_sel[1]), f"Relatorio_Ted_{p_sel[0]}.pdf")
            with c_xls: st.download_button("📊 Excel", to_excel_native(df_f), f"Relatorio_Ted_{p_sel[0]}.xlsx")
            with st.form("form_agenda"):
                btn_salvar = st.form_submit_button("💾 Salvar Tudo")
                for d in sorted(df_f['data'].unique(), reverse=True):
                    st.markdown(f"#### 🗓️ {d.strftime('%d/%m/%Y')}")
                    for area in ORDEM_AREAS:
                        df_area_f = df_f[(df_f['data'] == d) & (df_f['area'] == area)]
                        if not df_area_f.empty:
                            st.markdown(f"<p class='area-header'>📍 {area}</p>", unsafe_allow_html=True)
                            st.data_editor(df_area_f[['realizado', 'executor', 'prefixo', 'inicio_disp', 'fim_disp', 'turno', 'descricao', 'id', 'id_chamado']], 
                                column_config={"realizado": st.column_config.CheckboxColumn("OK", width="small"), "id": None, "id_chamado": None}, 
                                hide_index=True, use_container_width=True, key=f"ed_ted_{d}_{area}")
                if btn_salvar:
                    with engine.connect() as conn:
                        for key in st.session_state.keys():
                            if key.startswith("ed_ted_") and st.session_state[key]["edited_rows"]:
                                dt_r, ar_r = key.split("_")[2], key.split("_")[3]
                                df_rows = df_f[(df_f['data'].astype(str) == dt_r) & (df_f['area'] == ar_r)]
                                for idx, changes in st.session_state[key]["edited_rows"].items():
                                    row_data = df_rows.iloc[idx]; rid, id_ch = int(row_data['id']), row_data['id_chamado']
                                    for col, val in changes.items():
                                        conn.execute(text(f"UPDATE tarefas SET {col} = :v WHERE id = :i"), {"v": str(val), "i": rid})
                                        if col == 'realizado' and val is True and id_ch: conn.execute(text("UPDATE chamados SET status = 'Concluído' WHERE id = :ic"), {"ic": int(id_ch)})
                    conn.commit(); st.success("✅ Alterações salvas!"); st.rerun()

    elif aba_ativa == "📋 Cadastro Direto":
        st.subheader("📝 Agendamento Direto")
        st.info("💡 **Atenção:** Use este formulário para serviços que não vieram de chamados.")
        st.warning("⚠️ **Nota:** Para reagendar ou corrigir, basta alterar diretamente na lista abaixo. O salvamento é automático.")
        with st.form("f_d", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: d_i = st.date_input("Data", datetime.now())
            with c2: e_i = st.text_input("Executor")
            with c3: p_i = st.text_input("Prefixo")
            with c4: a_i = st.selectbox("Área", ORDEM_AREAS)
            ds_i, t_i = st.text_area("Descrição"), st.selectbox("Turno", LISTA_TURNOS)
            if st.form_submit_button("Confirmar Agendamento"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, origem) VALUES (:dt, :ex, :pr, '00:00', '00:00', :ds, :ar, :tu, 'Direto')"), {"dt": str(d_i), "ex": e_i, "pr": p_i, "ds": ds_i, "ar": a_i, "tu": t_i})
                    conn.commit()
                st.success("✅ Serviço cadastrado!"); st.rerun()
        st.divider(); st.subheader("📋 Lista de serviços")
        df_lista = pd.read_sql("SELECT * FROM tarefas ORDER BY data DESC, id DESC", engine)
        if not df_lista.empty:
            df_lista['data'] = pd.to_datetime(df_lista['data']).dt.date
            df_lista['Exc'] = False
            ed_l = st.data_editor(df_lista[['Exc', 'data', 'turno', 'executor', 'prefixo', 'descricao', 'area', 'id']], hide_index=True, use_container_width=True, key="ed_lista")
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
        st.subheader("📥 Aprovação de Chamados")
        st.info("💡 Preencha os campos e marque 'Aprovar' na última coluna para enviar à agenda.")
        df_p = pd.read_sql("SELECT id, data_solicitacao, prefixo, descricao FROM chamados WHERE status = 'Pendente' ORDER BY id DESC", engine)
        if not df_p.empty:
            if 'df_ap_work' not in st.session_state:
                df_p['Executor'] = "Pendente"; df_p['Area_Destino'] = "Mecânica"; df_p['Data_Programada'] = datetime.now().date(); df_p['Aprovar'] = False
                st.session_state.df_ap_work = df_p
            ed_c = st.data_editor(st.session_state.df_ap_work, hide_index=True, use_container_width=True, column_config={"data_solicitacao": "Aberto em", "Data_Programada": st.column_config.DateColumn("Data Programada"), "Area_Destino": st.column_config.SelectboxColumn("Área", options=ORDEM_AREAS), "Aprovar": st.column_config.CheckboxColumn("Aprovar?"), "id": None}, key="editor_chamados")
            if st.button("Processar Agendamentos"):
                selecionados = ed_c[ed_c['Aprovar'] == True]
                if not selecionados.empty:
                    with engine.connect() as conn:
                        for _, r in selecionados.iterrows():
                            conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, id_chamado, origem) VALUES (:dt, :ex, :pr, '00:00', '00:00', :ds, :ar, 'Não definido', :ic, 'Chamado')"), {"dt": str(r['Data_Programada']), "ex": r['Executor'], "pr": r['prefixo'], "ds": r['descricao'], "ar": r['Area_Destino'], "ic": r['id']})
                            conn.execute(text("UPDATE chamados SET status = 'Agendado' WHERE id = :id"), {"id": r['id']})
                        conn.commit(); st.success("✅ Agendamentos processados!"); del st.session_state.df_ap_work; st.rerun()
        else: st.info("Nenhum chamado pendente no momento.")

    elif aba_ativa == "📊 Indicadores":
        st.subheader("📊 Painel de Performance Operacional")
        st.info("💡 **Dica:** Utilize esses dados para identificar gargalos e planejar a capacidade da oficina.")
        c1, c2 = st.columns(2)
        df_ind = pd.read_sql("SELECT area, realizado FROM tarefas", engine)
        with c1:
            st.markdown("**Serviços por Área**"); st.bar_chart(df_ind['area'].value_counts(), color=COR_AZUL)
            st.caption("🔍 **O que isso mostra?** Identifica quais setores da oficina estão com maior carga.")
        with c2: 
            if not df_ind.empty:
                df_st = df_ind['realizado'].map({True: 'Concluído', False: 'Pendente'}).value_counts()
                st.markdown("**Status de Conclusão**"); st.bar_chart(df_st, color=COR_VERDE)
                st.caption("🔍 **O que isso mostra?** Mede a eficiência de entrega da equipe.")
        st.divider(); st.markdown("**⏳ Tempo de Resposta (Lead Time)**")
        query_lead = "SELECT c.data_solicitacao, t.data as data_conclusao FROM chamados c JOIN tarefas t ON c.id = t.id_chamado WHERE t.realizado = True"
        df_lead = pd.read_sql(query_lead, engine)
        if not df_lead.empty:
            df_lead['data_solicitacao'], df_lead['data_conclusao'] = pd.to_datetime(df_lead['data_solicitacao']), pd.to_datetime(df_lead['data_conclusao'])
            df_lead['dias'] = (df_lead['data_conclusao'] - df_lead['data_solicitacao']).dt.days.apply(lambda x: max(x, 0))
            col_m1, col_m2 = st.columns([0.3, 0.7])
            with col_m1: st.metric("Lead Time Médio", f"{df_lead['dias'].mean():.1f} Dias"); st.caption("🔍 Média entre chamado e entrega.")
            with col_m2: df_ev = df_lead.groupby('data_conclusao')['dias'].mean().reset_index(); st.line_chart(df_ev.set_index('data_conclusao'), color=COR_AZUL)
        else: st.warning("Dados de Lead Time ainda não disponíveis.")
