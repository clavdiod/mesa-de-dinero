from mesa.nucleo.almacen import almacen_por_defecto
from mesa.agentes import biblioteca as B
t = almacen_por_defecto().get(B.CLAVE) or {}
caja = sorted(((v["lynch"]["caja_neta_pct"], k) for k, v in t.items() if (v.get("lynch") or {}).get("caja_neta_pct") and v["lynch"]["caja_neta_pct"] > 10 and v["lynch"]["categoria"] != "ciclica"), reverse=True)
combo = [k for k, v in t.items() if B.es_combo_lynch(v.get("lynch"))]
print(f"::notice::con datos de Lynch {sum(1 for v in t.values() if v.get('lynch'))} · caja neta >10% (no cíclicas): {caja[:12]} · crece+PEG<1+poca deuda: {combo[:15]}")
print("::notice::NVDA " + (t.get("NVDA") or {}).get("frase_lynch", ""))
