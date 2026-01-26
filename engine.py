THEME = {
    "bg": "#111827", 
    "accent": "#ff7a00", 
    "card": "#1f2937", 
    "text": "#f3f4f6", 
    "error": "#f87171",
    "warning": "#facc15", 
    "success": "#4caf50"
}
ASSERTIVITY_CUTOFF = 85

def calculate_score_details(checklist_model, checklist_state):
    """
    Calcula a nota final da monitoria com base no checklist e status.
    Regra: Subtrai o peso de cada NC e zera a nota se houver NC Grave.
    """
    # 1. INICIALIZAÇÃO
    total_score = 100.0
    weight_deducted = 0
    nc_count = 0
    ncg_count = 0
    nc_items = []
    has_ncg = False

    # 2. ITERAÇÃO E SUBTRAÇÃO
    for item in checklist_model:
        val = checklist_state.get(item["id"])
        weight = item["weight"] or 0

        if val is None or val == 'nsa':
            continue

        if val == 'nc' or val == 'nc_grave':
            nc_count += 1
            nc_items.append(item)
            weight_deducted += weight
            total_score -= weight

            if val == 'nc_grave':
                ncg_count += 1
                has_ncg = True

    # Garante que a nota não seja negativa
    if total_score < 0:
        total_score = 0.0

    # 3. APLICAÇÃO DO CRITÉRIO ZERADOR (NC Grave)
    final_nota = total_score
    if has_ncg:
        final_nota = 0.0

    return {
        "finalNota": final_nota,
        "weightDeducted": weight_deducted,
        "ncCount": nc_count,
        "ncgCount": ncg_count,
        "ncItems": nc_items,
        "hasNCG": has_ncg,
    }