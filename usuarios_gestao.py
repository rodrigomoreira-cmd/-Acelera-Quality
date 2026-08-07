import streamlit as st
import pandas as pd
import hashlib
import time
from database import get_all_records_db, supabase, registrar_auditoria


def hash_password(password):
    """Gera o hash SHA-256 da senha."""
    return hashlib.sha256(str.encode(password.strip())).hexdigest()


def render_usuario_gestao():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados. Verifique suas credenciais.")
        return
    # ------------------------------------------------------------------

    # 🎨 PALETA DE CORES SISTÊMICA
    COR_PRINCIPAL = "#FF7A00"  # Laranja vibrante principal
    COR_SUCESSO = "#00E676"  # Verde neon
    COR_PERIGO = "#FF4B4B"  # Vermelho Alerta
    COR_TEXTO = "#A0AEC0"

    st.title("👥 Gestão de Equipe e Acessos")
    st.markdown(
        "Gerencie os colaboradores, níveis de acesso, status e redefina senhas perdidas."
    )

    nivel_logado = str(st.session_state.get("nivel", "USUARIO")).upper()
    dept_logado = str(st.session_state.get("departamento", "Todos"))
    nome_logado = str(st.session_state.get("user_nome", "Desconhecido"))

    # Proteção de acesso: Apenas liderança pode entrar
    if nivel_logado not in ["ADMIN", "GESTAO", "GERENCIA"]:
        st.error(
            "🚫 Acesso restrito. Apenas administradores e gestores podem visualizar esta página."
        )
        return

    df_users = get_all_records_db("usuarios")
    if df_users is None or df_users.empty:
        st.warning("Nenhum usuário encontrado na base de dados.")
        return

    # ==========================================================
    # 🛡️ TRAVA DE SEGURANÇA E VISIBILIDADE
    # ==========================================================
    # 1. Oculta o Admin Mestre para todos (Segurança de raiz)
    df_users = df_users[
        (
            ~df_users["email"]
            .astype(str)
            .str.contains("admin@grupoacelerador.com.br", na=False, case=False)
        )
        & (
            ~df_users["nome"]
            .astype(str)
            .str.contains("admin@grupoacelerador.com.br", na=False, case=False)
        )
    ].copy()

    # 2. Se NÃO for ADMIN, não pode ver outros admins (Evita escalada de privilégios)
    if nivel_logado != "ADMIN":
        df_users = df_users[
            df_users["nivel"].astype(str).str.upper() != "ADMIN"
        ].copy()

    # ==========================================================
    # FILTRO DE DEPARTAMENTO (Quem o gestor pode editar?)
    # ==========================================================
    if nivel_logado in ["ADMIN", "GERENCIA"]:
        df_filtrado = df_users.copy()
    else:
        # Gestão comum vê apenas o seu próprio departamento
        df_filtrado = df_users[
            df_users["departamento"].astype(str).str.upper() == dept_logado.upper()
        ].copy()

    # Padroniza a leitura do campo "ativo" do banco (Lida com 'esta_ativo' e 'ativo')
    def checar_ativo(row):
        v_esta = row.get("esta_ativo")
        v_at = row.get("ativo")
        if str(v_esta).lower() in ["true", "1", "sim"] or str(v_at).lower() in [
            "true",
            "1",
            "sim",
        ]:
            return True
        if str(v_esta).lower() in ["false", "0", "nao"] or str(v_at).lower() in [
            "false",
            "0",
            "nao",
        ]:
            return False
        return True  # Default caso seja nulo

    df_filtrado["is_ativo_clean"] = df_filtrado.apply(checar_ativo, axis=1)
    df_filtrado = df_filtrado.sort_values(
        by=["is_ativo_clean", "nome"], ascending=[False, True]
    )

    # ==========================================================
    # 📊 PAINEL DE INDICADORES (CARDS PREMIUM HTML)
    # ==========================================================
    qtd_total = len(df_filtrado)
    qtd_ativos = len(df_filtrado[df_filtrado["is_ativo_clean"] == True])
    qtd_inativos = qtd_total - qtd_ativos

    def render_kpi_card(title, value, icon="", border_color=COR_PRINCIPAL):
        return f"""
        <div style="background-color: rgba(255,255,255,0.02); padding: 20px; border-radius: 12px; border-left: 5px solid {border_color}; border-top: 1px solid rgba(255,255,255,0.05); border-right: 1px solid rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            <p style="margin:0; font-size: 13px; color: {COR_TEXTO}; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">{icon} {title}</p>
            <h2 style="margin:10px 0 0 0; color: #fff; font-size: 32px; font-weight: 700;">{value}</h2>
        </div>
        """

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            render_kpi_card("Total de Colaboradores", qtd_total, "👥", "#1f77b4"),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_kpi_card("Contas Ativas", qtd_ativos, "✅", COR_SUCESSO),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            render_kpi_card("Contas Inativas", qtd_inativos, "🚫", COR_PERIGO),
            unsafe_allow_html=True,
        )

    st.write("##")
    st.divider()

    # ==========================================================
    # SELEÇÃO DE USUÁRIO PARA EDIÇÃO
    # ==========================================================
    st.markdown("### ⚙️ Selecionar e Editar Colaborador")
    st.caption(
        "Escolha um usuário da lista para alterar permissões, bloquear o acesso ou resetar a senha."
    )

    opcoes_formatadas = []
    mapa_usuarios = {}

    for _, row in df_filtrado.iterrows():
        is_active = row["is_ativo_clean"]
        status_icone = "🟢" if is_active else "🔴"
        status_texto = "" if is_active else " (Inativo)"
        label = f"{status_icone} {row.get('nome', 'Sem Nome')}{status_texto}"
        opcoes_formatadas.append(label)
        mapa_usuarios[label] = row["id"]

    escolha = st.selectbox(
        "Busque o colaborador:", [""] + opcoes_formatadas, label_visibility="collapsed"
    )

    if escolha:
        st.write("##")
        user_id = mapa_usuarios[escolha]
        user_data = df_filtrado[df_filtrado["id"] == user_id].iloc[0]

        # Pega a foto se tiver para exibir bonitinho
        foto_usr = user_data.get("foto_url")
        foto_html = (
            f'<img src="{foto_usr}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover; border: 2px solid {COR_PRINCIPAL};">'
            if foto_usr and str(foto_usr).startswith("http")
            else f'<div style="font-size: 35px;">👤</div>'
        )

        c_form, c_acoes = st.columns([2, 1.2], gap="large")
        ALTURA_CAIXAS = 450

        # ==========================================================
        # FORMULÁRIO DE EDIÇÃO CADASTRAL
        # ==========================================================
        with c_form:
            with st.container(height=ALTURA_CAIXAS, border=True):
                # Headerzinho do form
                st.markdown(
                    f"""
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                    {foto_html}
                    <div>
                        <h4 style="margin: 0; color: {COR_PRINCIPAL};">Dados de Cadastro</h4>
                        <span style="font-size: 12px; color: {COR_TEXTO};">ID: {str(user_id)[:8]}...</span>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # BORDER=FALSE para não ter linha dupla!
                with st.form(f"form_edit_{user_id}", border=False):
                    novo_nome = st.text_input(
                        "Nome Completo", value=str(user_data.get("nome", ""))
                    )
                    novo_email = st.text_input(
                        "E-mail / Login", value=str(user_data.get("email", ""))
                    )

                    col_d, col_n = st.columns(2)

                    # Tratamento de Departamento
                    opcoes_dept = [
                        "SDR",
                        "Especialista",
                        "Venda de Ingresso",
                        "Auditor",
                        "Gestão",
                        "Gerência",
                        "Outros",
                    ]
                    dept_atual = str(user_data.get("departamento", "SDR"))
                    if dept_atual not in opcoes_dept:
                        opcoes_dept.append(dept_atual)
                    novo_dept = col_d.selectbox(
                        "Departamento", opcoes_dept, index=opcoes_dept.index(dept_atual)
                    )

                    # Tratamento de Nível de Acesso
                    opcoes_nivel = ["USUARIO", "AUDITOR", "GESTAO", "GERENCIA", "ADMIN"]
                    nivel_atual = str(user_data.get("nivel", "USUARIO")).upper()
                    if nivel_atual not in opcoes_nivel:
                        opcoes_nivel.append(nivel_atual)

                    # Proteção: Apenas um ADMIN pode dar privilégios de ADMIN para alguém
                    pode_editar_nivel = nivel_logado == "ADMIN"
                    novo_nivel = col_n.selectbox(
                        "Nível de Acesso",
                        opcoes_nivel,
                        index=opcoes_nivel.index(nivel_atual),
                        disabled=not pode_editar_nivel,
                        help=(
                            "Apenas o Administrador Geral pode alterar o Nível de Acesso."
                            if not pode_editar_nivel
                            else ""
                        ),
                    )

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Toggle de Ativar/Desativar com visual moderno
                    status_atual = user_data["is_ativo_clean"]
                    novo_status = st.toggle(
                        "Conta Ativada (Permitir Login)", value=bool(status_atual)
                    )

                    # Botão de envio
                    st.write("")
                    btn_save = st.form_submit_button(
                        "💾 Salvar Alterações", type="primary", use_container_width=True
                    )

                    if btn_save:
                        # ✨ A MÁGICA DO BANCO DE DADOS: Força as duas colunas a ficarem iguais!
                        payload = {
                            "nome": novo_nome,
                            "email": novo_email,
                            "departamento": novo_dept,
                            "nivel": novo_nivel,
                            "ativo": novo_status,  # Coluna 1
                            "esta_ativo": novo_status,  # Coluna 2 (Acaba com os fantasmas)
                        }
                        try:
                            supabase.table("usuarios").update(payload).eq("id", user_id).execute()  # type: ignore
                            registrar_auditoria(
                                "EDICAO_USUARIO",
                                f"Atualizou cadastro de {novo_nome}. Status: {'Ativo' if novo_status else 'Inativo'}",
                                novo_nome,
                                nome_logado,
                            )
                            st.success(f"✅ Cadastro atualizado com sucesso!")
                            get_all_records_db.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco de dados: {e}")

        # ==========================================================
        # PAINEL DE AÇÕES CRÍTICAS (SENHA E EXCLUSÃO)
        # ==========================================================
        with c_acoes:
            with st.container(height=ALTURA_CAIXAS, border=True):
                st.markdown(
                    f"<h4 style='color: {COR_PERIGO};'>🔐 Área de Segurança</h4>",
                    unsafe_allow_html=True,
                )
                st.caption("Ações críticas e irreversíveis da conta.")
                st.write("")

                # MODAL PARA REDEFINIR SENHA COM HASH
                @st.dialog("🔑 Redefinir Senha de Acesso")
                def modal_senha():
                    st.warning(
                        f"Redefinir a senha de **{user_data.get('nome', 'Usuário')}**?"
                    )
                    st.markdown(
                        "Crie uma nova senha temporária. A senha será criptografada imediatamente."
                    )
                    nova_senha = st.text_input(
                        "Nova Senha:", value="Mudar123", type="password"
                    )

                    if st.button(
                        "Confirmar Troca", type="primary", use_container_width=True
                    ):
                        if len(nova_senha) < 4:  # Consistente com cadastro.py (4 chars)
                            st.error("A senha deve ter no mínimo 4 caracteres.")
                        else:
                            try:
                                # AQUI ESTÁ A CORREÇÃO DE SEGURANÇA! (hash_password)
                                senha_criptografada = hash_password(nova_senha)
                                supabase.table("usuarios").update({"senha": senha_criptografada}).eq("id", user_id).execute()  # type: ignore
                                registrar_auditoria(
                                    "REDEFINICAO_SENHA",
                                    "A senha foi resetada pela liderança.",
                                    str(user_data.get("nome", "")),
                                    nome_logado,
                                )
                                st.success(
                                    "✅ Senha alterada com sucesso! Avise o colaborador."
                                )
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

                if st.button("🔑 Gerar Nova Senha", use_container_width=True):
                    modal_senha()

                st.write("---")

                st.info(
                    "💡 **Dica de Desligamento:** Nunca delete um usuário. Apenas desmarque o botão **'Conta Ativada'** no formulário ao lado. Isso revoga o acesso da pessoa imediatamente, mas preserva todo o histórico de monitorias dela nos relatórios da empresa."
                )