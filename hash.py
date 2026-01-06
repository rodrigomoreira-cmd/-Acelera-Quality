import streamlit_authenticator as stauth

# Liste aqui as senhas que você deseja transformar em Hash
senhas_para_gerar = ['senha_admin_123', 'senha_paulo_456', 'senha_lane_789']

print("--- GERANDO HASHES ---")

for senha in senhas_para_gerar:
    # Usamos o método manual de hash para evitar erros de estrutura de dicionário
    hash_gerado = stauth.Hasher.hash(senha)
    print(f"Senha: {senha}")
    print(f"Hash: {hash_gerado}")
    print("-" * 30)