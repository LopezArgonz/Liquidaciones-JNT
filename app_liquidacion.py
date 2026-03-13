import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import re
import requests

import io

class LiquidadorLaboral:
    def __init__(self, caratula, ingreso, despido, sueldo, causa="Sin Causa", art1=False, art2=False, ipc_inicio=1.0, ipc_fin=1.0, fuente_ipc="INDEC", tasa_tim=0.0, aplicar_vizzoti=False, tope_cct=None, rubros_adicionales=None, fecha_capitalizacion=None, tasa_tim_2=0.0):
        self.caratula = caratula
        self.ingreso = datetime.strptime(ingreso, "%d/%m/%Y")
        self.despido = datetime.strptime(despido, "%d/%m/%Y")
        self.sueldo = sueldo
        self.causa = causa
        self.art1 = art1
        self.art2 = art2
        self.ipc_inicio = ipc_inicio
        self.ipc_fin = ipc_fin
        self.fuente_ipc = fuente_ipc
        self.tasa_tim = tasa_tim
        self.tasa_tim_2 = tasa_tim_2 # Tasa desde capitalización hasta hoy
        self.fecha_capitalizacion = fecha_capitalizacion # Fecha de corte para capitalizar
        self.aplicar_vizzoti = aplicar_vizzoti
        self.tope_cct = tope_cct
        self.rubros_adicionales = rubros_adicionales if rubros_adicionales else []

        self.antiguedad = relativedelta(self.despido, self.ingreso)
        self.hoy = datetime.now()

    def calcular_periodos_245(self):
        anios = self.antiguedad.years
        meses = self.antiguedad.months
        if meses > 3:
            anios += 1
        return anios

    def calcular_base_245(self):
        """Calcula la base indemnizatoria aplicando Vizzoti si corresponde"""
        if not self.aplicar_vizzoti or not self.tope_cct:
            return self.sueldo
        
        tope_vizzoti = self.sueldo * 0.67
        
        # Si el tope convencional es MENOR al 67% del sueldo real, es confiscatorio.
        # En ese caso, la base es el 67% del sueldo (piso Vizzoti).
        if self.tope_cct < tope_vizzoti:
            return tope_vizzoti
        else:
             # Si el tope NO es confiscatorio (es mayor al 67%), se aplica el tope CCT.
            return min(self.sueldo, self.tope_cct)

    def calcular_integracion_mes(self):
        ultimo_dia = calendar.monthrange(self.despido.year, self.despido.month)[1]
        dias_faltantes = ultimo_dia - self.despido.day
        return (self.sueldo / 30) * dias_faltantes if self.causa == "Sin Causa" else 0

    def calcular_sac_prop(self):
        inicio_sem = datetime(self.despido.year, 1, 1) if self.despido.month <= 6 else datetime(self.despido.year, 7, 1)
        dias = (self.despido - inicio_sem).days + 1
        return (self.sueldo / 2) * (dias / 182)

    def calcular_vacaciones_prop(self):
        anios = self.antiguedad.years
        escala = 14 if anios < 5 else 21 if anios < 10 else 28 if anios < 20 else 35
        dias_anio = (self.despido - datetime(self.despido.year, 1, 1)).days + 1
        monto_vac = (dias_anio / 365) * escala * (self.sueldo / 25)
        return monto_vac * 1.0833

    def calcular_dias_trabajados_mes_despido(self):
        """Calcula el proporcional de días trabajados en el mes del despido"""
        # Cantidad de días total del mes del despido
        dias_totales_mes = calendar.monthrange(self.despido.year, self.despido.month)[1]
        dia_despido = self.despido.day
        
        # Proporcional: (Sueldo / Días del mes) * Días trabajados (incluye día despido)
        return (self.sueldo / dias_totales_mes) * dia_despido

    def generar_excel(self, buffer=None):
        if buffer:
            writer = pd.ExcelWriter(buffer, engine='xlsxwriter')
        else:
            caratula_limpia = re.sub(r'[^\w\s-]', '_', self.caratula).strip().replace(' ', '_')
            nombre_archivo = f"Liquidacion_{caratula_limpia}.xlsx"
            writer = pd.ExcelWriter(nombre_archivo, engine='xlsxwriter')
            
        workbook = writer.book
        ws = workbook.add_worksheet('Liquidación')
        
        fmt_tit = workbook.add_format({'bold': True, 'bg_color': '#2F5597', 'font_color': 'white', 'border': 1, 'align': 'center'})
        fmt_mon = workbook.add_format({'num_format': '$#,##0.00', 'border': 1})
        fmt_txt = workbook.add_format({'border': 1})
        fmt_bold = workbook.add_format({'bold': True, 'border': 1})
        fmt_int = workbook.add_format({'bold': True, 'bg_color': '#EBF1DE', 'border': 1})

        ws.set_column('A:A', 50); ws.set_column('B:B', 25)

        ws.write('A1', 'EXPEDIENTE:', fmt_bold); ws.write('B1', self.caratula, fmt_txt)
        ws.write('A2', 'FECHA DE DESPIDO:', fmt_bold); ws.write('B2', self.despido.strftime("%d/%m/%Y"), fmt_txt)
        
        metodo_act = f"IPC {self.fuente_ipc} + 3% Anual" if self.fuente_ipc != "TIM BCRA" else f"Tasa TIM BCRA ({self.tasa_tim}%)"
        ws.write('A3', 'MÉTODO ACTUALIZACIÓN:', fmt_bold); ws.write('B3', metodo_act, fmt_txt)
        
        ws.write('A5', 'RUBRO (VALORES HISTÓRICOS)', fmt_tit); ws.write('B5', 'MONTO', fmt_tit)

        rubros = []
        total_historico = 0.0

        monto_245 = 0.0
        monto_preaviso = 0.0
        monto_integracion = 0.0

        # Rubro: Días trabajados (mes despido) - SE CALCULA SIEMPRE
        monto_dias_trabajados = self.calcular_dias_trabajados_mes_despido()
        rubros.append((f"Días trabajados mes despido ({self.despido.day} días)", monto_dias_trabajados))
        total_historico += monto_dias_trabajados

        if self.causa == "Sin Causa":
            periodos = self.calcular_periodos_245()
            base_indemnizatoria = self.calcular_base_245()
            
            monto_245 = base_indemnizatoria * periodos
            monto_245 = base_indemnizatoria * periodos
            label_245 = f"Indemnización por antigüedad (art. 245 LCT cfr. tope \"Vizzoti\" CSJN) ({periodos} años)" if self.aplicar_vizzoti else f"Indemnización por antigüedad (art. 245 LCT) ({periodos} años)"
            rubros.append([label_245, monto_245])
            total_historico += monto_245
            
            # Preaviso
            meses_preaviso = 2 if self.antiguedad.years >= 5 else 1
            monto_preaviso = self.sueldo * meses_preaviso
            rubros.append([f"Indemnización sustitutiva del preaviso (art. 232 LCT) ({meses_preaviso} mes/es)", monto_preaviso])
            total_historico += monto_preaviso

            # SAC sobre Preaviso
            sac_preaviso = monto_preaviso / 12
            rubros.append(["SAC sobre preaviso", sac_preaviso])
            total_historico += sac_preaviso

            # Integración Mes de Despido
            monto_integracion = self.calcular_integracion_mes()
            rubros.append(["Integración del mes de despido (art. 233 LCT)", monto_integracion])
            total_historico += monto_integracion

            # SAC sobre Integración
            sac_integracion = monto_integracion / 12
            rubros.append(["SAC sobre integración", sac_integracion])
            total_historico += sac_integracion
        
        # Multas (Base de cálculo suele ser sobre la indemnización o sueldos dependiendo el criterio,
        # simplificado aquí usando la misma base o sueldo según corresponda, usualmente es sobre el 245)
        # Art 1 Ley 25323: Igual a la indemnización por antigüedad
        if self.art1: 
             monto_art1 = monto_245 
             rubros.append(["Art. 1º Ley 25.323", monto_art1])
             total_historico += monto_art1

        # Art 2 Ley 25323: 50% de (Antigüedad + Preaviso + Integración)
        if self.art2:
            base_multa = monto_245 + monto_preaviso + monto_integracion
            monto_art2 = base_multa * 0.5
            rubros.append(["Art. 2º Ley 25.323", monto_art2])
            total_historico += monto_art2

        # SAC Proporcional
        sac_proporcional = self.calcular_sac_prop()
        rubros.append(["SAC Proporcional", sac_proporcional])
        total_historico += sac_proporcional

        # Vacaciones Proporcionales
        vacaciones_proporcionales = self.calcular_vacaciones_prop()
        rubros.append(["Vacaciones Proporcionales (c/ SAC)", vacaciones_proporcionales])
        total_historico += vacaciones_proporcionales

        # Rubros Adicionales
        if self.rubros_adicionales:
            for concepto, monto in self.rubros_adicionales:
                rubros.append([concepto, float(monto)])
                total_historico += float(monto)

        row = 6
        for lab, mon in rubros:
            ws.write(row, 0, lab, fmt_txt); ws.write(row, 1, mon, fmt_mon)
            row += 1

        row += 1
        ws.write(row, 0, f"ACTUALIZACIÓN E INTERESES (Fuente: {self.fuente_ipc})", fmt_tit)
        ws.write(row, 1, "", fmt_tit)
        
        cap_act = 0.0
        int_puro = 0.0
        
        if self.fuente_ipc == "TIM BCRA":
            # Actualización por TASA (Variable 1197 BCRA)
            ws.write(row+1, 0, "Capital Histórico Total:", fmt_txt); ws.write(row+1, 1, total_historico, fmt_mon)
            
            if self.fecha_capitalizacion:
                # Caso CON Capitalización de Intereses
                ws.write(row+2, 0, f"INTERESES PERÍODO 1 (Despido -> {self.fecha_capitalizacion}):", fmt_bold)
                ws.write(row+3, 0, f"Tasa Acumulada P1:", fmt_txt); ws.write(row+3, 1, f"{self.tasa_tim}%", fmt_txt)
                
                monto_interes_1 = total_historico * (self.tasa_tim / 100)
                ws.write(row+4, 0, "Monto Intereses P1:", fmt_txt); ws.write(row+4, 1, monto_interes_1, fmt_mon)
                
                capital_capitalizado = total_historico + monto_interes_1
                ws.write(row+5, 0, "NUEVO CAPITAL (Capitalizado):", fmt_bold); ws.write(row+5, 1, capital_capitalizado, fmt_mon)
                
                ws.write(row+6, 0, f"INTERESES PERÍODO 2 ({self.fecha_capitalizacion} -> Actualidad):", fmt_bold)
                ws.write(row+7, 0, f"Tasa Acumulada P2:", fmt_txt); ws.write(row+7, 1, f"{self.tasa_tim_2}%", fmt_txt)
                
                monto_interes_2 = capital_capitalizado * (self.tasa_tim_2 / 100)
                ws.write(row+8, 0, "Monto Intereses P2:", fmt_txt); ws.write(row+8, 1, monto_interes_2, fmt_mon)
                
                cap_act = capital_capitalizado + monto_interes_2
                
                ws.write(row+10, 0, "TOTAL FINAL (Capital + Int. Capitalizados):", fmt_int); ws.write(row+10, 1, cap_act, fmt_int)
                
            else:
                # Caso SIN Capitalización (Simple)
                ws.write(row+2, 0, f"Tasa Interés Acumulada:", fmt_txt); ws.write(row+2, 1, f"{self.tasa_tim}%", fmt_txt)
                
                monto_interes = total_historico * (self.tasa_tim / 100)
                ws.write(row+3, 0, "MONTO INTERESES:", fmt_bold); ws.write(row+3, 1, monto_interes, fmt_mon)
                
                cap_act = total_historico + monto_interes # Total final
                
                # Ajuste de visualización para TIM (sin interés puro aparte)
                ws.write(row+6, 0, "TOTAL FINAL (Capital + Tasa):", fmt_int); ws.write(row+6, 1, cap_act, fmt_int)
            
        else:
            # Actualización por IPC + 3%
            coef = self.ipc_fin / self.ipc_inicio
            cap_act = total_historico * coef
            dif = relativedelta(self.hoy, self.despido)
            t_anios = dif.years + (dif.days / 365) + (dif.months / 12) # Aproximacion de años para interes
            int_puro = cap_act * (0.03 * t_anios)

            ws.write(row+1, 0, "Capital Histórico Total:", fmt_txt); ws.write(row+1, 1, total_historico, fmt_mon)
            ws.write(row+2, 0, f"Coeficiente IPC {self.fuente_ipc}:", fmt_txt); ws.write(row+2, 1, coef, workbook.add_format({'num_format': '0.0000', 'border': 1}))
            ws.write(row+3, 0, "CAPITAL ACTUALIZADO:", fmt_bold); ws.write(row+3, 1, cap_act, fmt_mon)
            ws.write(row+4, 0, f"Interés Puro (3% anual):", fmt_txt); ws.write(row+4, 1, int_puro, fmt_mon)
            ws.write(row+6, 0, "TOTAL FINAL ACTUALIZADO:", fmt_int); ws.write(row+6, 1, cap_act + int_puro, fmt_int)
        
        workbook.close()
        if not buffer:
             print(f"\n>>> ¡LIQUIDACIÓN CREADA CON ÉXITO! <<<")
def obtener_datos_online(fuente, fecha_inicio=None, fecha_fin=None, serie_id_personalizado=None):
    """
    Obtiene datos de la API de Datos Argentina.
    Si fuente es IPC (INDEC/CABA), devuelve el valor del índice para una fecha o el último disponible.
    Si fuente es TASAS (TIM BCRA), devuelve la Tasa Acumulada entre fecha_inicio y fecha_fin.
    """
    try:
        url = "https://apis.datos.gob.ar/series/api/series/"
        
        # IDs por defecto
        series_ids = {
            "INDEC": "145.3_INGNACUAL_DICI_M_38",
            "CABA": "11.3_INIVEL_GEN_DICI_M_26",
            "TIM BCRA": "168.1_T_ACT_G_D_D_0_38" # Default: Tasa Activa BNA (hasta que TIM tenga ID propio)
        }
        
        id_serie = serie_id_personalizado if serie_id_personalizado else series_ids.get(fuente)
        
        if not id_serie:
            return None

        # Si es IPC, la lógica es puntual (valor de fecha X o último)
        if fuente in ["INDEC", "CABA"]:
            params = {"ids": id_serie, "format": "json", "limit": 5000}
            response = requests.get(url, params=params, timeout=10).json()
            data = response['data']
            
            if fecha_inicio: # Usamos fecha_inicio como "fecha objetivo" para IPC
                f_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
                target = f_dt.strftime("%Y-%m-01")
                for entry in data:
                    if entry[0] == target: return entry[1]
                # Si no encuentra exacto, retorna el anterior inmediato (caso fechas intermedias)
                # Para simplificar, retornamos el último si no hay match (aunque lo ideal sería interpolar o buscar el mes)
                return data[-1][1] 
            else:
                # Retorna último valor y fecha
                last_entry = data[-1]
                return last_entry[1], datetime.strptime(last_entry[0], "%Y-%m-%d").strftime("%d/%m/%Y")

        # Si es TASA (BCRA), usamos la API oficial del BCRA para la variable 1197 (TIM)
        elif fuente == "TIM BCRA":
            # Variable 1197: Tasa de Intereses Moratorios (TIM) - Es un coeficiente/índice
            id_variable_bcra = "1197"
            url_bcra = f"https://api.bcra.gob.ar/estadisticas/v3.0/monetarias/{id_variable_bcra}"
            
            if not fecha_inicio: return 0.0
            
            # Formato fecha para API BCRA: YYYY-MM-DD
            f_ini_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
            f_fin_dt = datetime.strptime(fecha_fin, "%d/%m/%Y") if fecha_fin else datetime.now()
            
            desde_str = f_ini_dt.strftime("%Y-%m-%d")
            hasta_str = f_fin_dt.strftime("%Y-%m-%d")
            
            params = {
                "desde": desde_str,
                "hasta": hasta_str
            }
            
            # Solicitud a API BCRA (sin verificar SSL por problemas comunes con certificados gubernamentales, o manejando excepción)
            response = requests.get(url_bcra, params=params, timeout=15, verify=False) # verify=False a veces es necesario en ent. locales
            
            if response.status_code != 200:
                print(f"Error BCRA: {response.status_code}")
                # Fallbck: Intentar sin fechas si falla el filtrado, o retornar error
                return None
                
            data = response.json().get('results', [])
            
            if not data:
                return None
                
            # La API devuelve lista ordenada por fecha descendente o ascendente.
            # Convertimos a lista de tuplas (fecha, valor) y ordenamos por fecha
            datos_ordenados = []
            for entry in data:
                try:
                    f_d = datetime.strptime(entry['fecha'], "%Y-%m-%d")
                    val = float(entry['valor'])
                    datos_ordenados.append((f_d, val))
                except: continue
                
            datos_ordenados.sort(key=lambda x: x[0]) # Ordenar ascendente
            
            if not datos_ordenados: return None
            
            # Buscar valor más cercano a fecha inicio (o el primero disponible)
            valor_inicio = None
            for d, v in datos_ordenados:
                if d >= f_ini_dt:
                    valor_inicio = v
                    break
            if valor_inicio is None: valor_inicio = datos_ordenados[0][1] # Fallback al más antiguo
            
            # Buscar valor más cercano a fecha fin (o el último disponible)
            valor_fin = datos_ordenados[-1][1]
            
            # Cálculo de Tasa Acumulada %: ((ValorFin / ValorInicio) - 1) * 100
            tasa_acumulada = ((valor_fin / valor_inicio) - 1) * 100
            
            return round(tasa_acumulada, 2)

    except Exception as e:
        print(f"Error API: {e}")
        return None

def solicitar_datos():
    print("\n" + "="*45 + "\n  LIQUIDADOR JUDICIAL - IPC INDEC/CABA\n" + "="*45)
    car = input("1. Carátula: ")
    ing = input("2. Fecha de ingreso (DD/MM/AAAA): ")
    des = input("3. Fecha de despido (DD/MM/AAAA): ")
    rem = input("4. Mejor Remuneración: ").replace(',', '.')
    
    print("\nFUENTE DE ACTUALIZACIÓN:\n1. IPC INDEC (Nacional)\n2. IPC CABA (Ciudad)")
    fnt = "INDEC" if input("Seleccione fuente (1 o 2): ") == "1" else "CABA"

    print(f"\n--- Conectando a Base de Datos de {fnt} ---")
    val_ini = obtener_ipc_online(fnt, des)
    res_fin = obtener_ipc_online(fnt) # Guardamos el resultado completo antes de desempaquetar
    
    if val_ini and res_fin:
        val_fin, fecha_fin = res_fin
        print(f"[*] IPC Mes Despido ({fnt}): {val_ini}")
        print(f"[*] Último IPC disponible ({fecha_fin}): {val_fin}")
        if input("\n¿Confirmar estos valores? (S/N): ").upper() != 'S':
            val_ini = float(input("Ingresar IPC Mes Despido manual: ").replace(',', '.'))
            val_fin = float(input("Ingresar IPC Actual manual: ").replace(',', '.'))
    else:
        print("[!] No se pudo conectar con la base de datos o no hay datos para esa fecha.")
        val_ini = float(input("Ingresar IPC Mes Despido manualmente: ").replace(',', '.'))
        val_fin = float(input("Ingresar IPC Actual (último disponible) manualmente: ").replace(',', '.'))

    a1 = input("\n¿Procede Art 1 Ley 25.323? (S/N): ").upper() == 'S'
    a2 = input("¿Procede Art 2 Ley 25.323? (S/N): ").upper() == 'S'
    
    return LiquidadorLaboral(car, ing, des, float(rem), art1=a1, art2=a2, ipc_inicio=val_ini, ipc_fin=val_fin, fuente_ipc=fnt)

if __name__ == "__main__":
    try:
        mi_caso = solicitar_datos()
        mi_caso.generar_excel()
    except Exception as e:
        print(f"\n[ERROR] {e}")