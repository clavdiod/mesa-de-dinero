from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
f = a.get("macro/cer_fichas") or {}
print("::notice::" + " | ".join(f"{k}: {str((v or {}).get('formaAmortizacion'))[:120]}" for k, v in f.items())[:6000])
