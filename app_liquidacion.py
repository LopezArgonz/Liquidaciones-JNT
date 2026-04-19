import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import re
import requests

import io

class LiquidadorLaboral:
    def __init__(self, caratula, ingreso, despido, sueldo, causa="Sin Causa", art1=False, art2=False, ipc_inicio=1.0, ipc_fin=1.0, aplicar_vizzoti=False, tope_cct=None, rubros_adicionales=None, fecha_liquidacion=None, incluir_sac_anterior=False, art80=False, dto34=False, art8_24013=False, art15_24013=False, pagos_a_cuenta=0.0):
        self.caratula = caratula
        self.ingreso = datetime.strptime(ingreso, "%d/%m/%Y")
        self.despido = datetime.strptime(despido, "%d/%m/%Y")
        if fecha_liquidacion:
            self.hoy = datetime.strptime(fecha_liquidacion, "%d/%m/%Y")
        else:
            self.hoy = datetime.now()
        self.sueldo = sueldo
        self.causa = causa
        self.art1 = art1
        self.art2 = art2
        self.art80 = art80
        self.art8_24013 = art8_24013
        self.art15_24013 = art15_24013
        self.dto34 = dto34
        self.ipc_inicio = ipc_inicio
        self.ipc_fin = ipc_fin
        self.aplicar_vizzoti = aplicar_vizzoti
        self.tope_cct = tope_cct
        self.rubros_adicionales = rubros_adicionales if rubros_adicionales else []
        self.incluir_sac_anterior = incluir_sac_anterior
        self.pagos_a_cuenta = pagos_a_cuenta

        self.antiguedad = relativedelta(self.despido, self.ingreso)

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

    def calcular_sac_semestre_anterior(self):
        """Si se marca la opción, calcula el SAC adeudado del semestre anterior (Enero o Julio)."""
        if self.incluir_sac_anterior and self.despido.month in (1, 7):
            if self.despido.month == 7:
                inicio_sem_ant = datetime(self.despido.year, 1, 1)
                fin_sem_ant = datetime(self.despido.year, 6, 30)
            else:
                inicio_sem_ant = datetime(self.despido.year - 1, 7, 1)
                fin_sem_ant = datetime(self.despido.year - 1, 12, 31)
            
            if self.ingreso > fin_sem_ant:
                return 0.0
                
            if self.ingreso <= inicio_sem_ant:
                return self.sueldo / 2
                
            fecha_inicio = max(inicio_sem_ant, self.ingreso)
            dias = (fin_sem_ant - fecha_inicio).days + 1
            return (self.sueldo / 365) * dias
        return 0.0

    def calcular_sac_prop(self):
        inicio_sem = datetime(self.despido.year, 1, 1) if self.despido.month <= 6 else datetime(self.despido.year, 7, 1)
        fecha_inicio_calculo = max(inicio_sem, self.ingreso)
        dias = (self.despido - fecha_inicio_calculo).days + 1
        return (self.sueldo / 365) * dias

    def calcular_vacaciones_prop(self):
        fecha_fin_anio = datetime(self.despido.year, 12, 31)
        antiguedad_al_31_dic = relativedelta(fecha_fin_anio, self.ingreso)
        anios = antiguedad_al_31_dic.years
        escala = 14 if anios < 5 else 21 if anios < 10 else 28 if anios < 20 else 35
        fecha_inicio_anio = max(datetime(self.despido.year, 1, 1), self.ingreso)
        dias_anio = (self.despido - fecha_inicio_anio).days + 1
        proporcional_dias = (escala * dias_anio / 365)
        monto_vac = (self.sueldo / 25) * proporcional_dias
        return monto_vac, proporcional_dias

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
        fmt_int = workbook.add_format({'bold': True, 'bg_color': '#EBF1DE', 'border': 1, 'num_format': '$#,##0.00'})

        ws.set_column('A:A', 50); ws.set_column('B:B', 25)

        ws.write('A1', 'EXPEDIENTE:', fmt_bold); ws.write('B1', self.caratula, fmt_txt)
        ws.write('A2', 'FECHA DE DESPIDO:', fmt_bold); ws.write('B2', self.despido.strftime("%d/%m/%Y"), fmt_txt)
        ws.write('A3', 'FECHA DE LIQUIDACIÓN:', fmt_bold); ws.write('B3', self.hoy.strftime("%d/%m/%Y"), fmt_txt)
        ws.write('A4', 'MÉTODO ACTUALIZACIÓN:', fmt_bold); ws.write('B4', "IPC INDEC + 3% Anual", fmt_txt)
        
        ws.write('A6', 'RUBRO (VALORES HISTÓRICOS)', fmt_tit); ws.write('B6', 'MONTO', fmt_tit)

        rubros = []
        total_historico = 0.0

        monto_245 = 0.0
        monto_preaviso = 0.0
        monto_integracion = 0.0

        # 1. Indemnización por antigüedad (art. 245 LCT)
        if self.causa == "Sin Causa":
            periodos = self.calcular_periodos_245()
            base_indemnizatoria = self.calcular_base_245()
            monto_245 = base_indemnizatoria * periodos
            label_245 = f"Indemnización por antigüedad (art. 245 LCT) ({periodos} años)"
            if self.aplicar_vizzoti:
                label_245 = f"Indemnización por antigüedad (art. 245 LCT cfr. tope \"Vizzoti\" CSJN) ({periodos} años)"
            rubros.append([label_245, monto_245])
            total_historico += monto_245

            # 2. Indemnización sustitutiva del preaviso (art. 232 LCT)
            meses_preaviso = 2 if self.antiguedad.years >= 5 else 1
            monto_preaviso = self.sueldo * meses_preaviso
            rubros.append([f"Indemnización sustitutiva del preaviso (art. 232 LCT) ({meses_preaviso} mes/es)", monto_preaviso])
            total_historico += monto_preaviso

            # 3. SAC sobre preaviso
            sac_preaviso = monto_preaviso / 12
            rubros.append(["SAC sobre preaviso", sac_preaviso])
            total_historico += sac_preaviso

            # 4. Integración del mes de despido (art. 233 LCT)
            monto_integracion = self.calcular_integracion_mes()
            if monto_integracion > 0:
                rubros.append(["Integración del mes de despido (art. 233 LCT)", monto_integracion])
                total_historico += monto_integracion

                # 5. SAC sobre integración
                sac_integracion = monto_integracion / 12
                rubros.append(["SAC sobre integración", sac_integracion])
                total_historico += sac_integracion

            # Dto. 34/2019 (Doble Indemnización)
            if self.dto34:
                monto_dto34 = monto_245 + monto_preaviso + sac_preaviso + monto_integracion + (monto_integracion / 12 if monto_integracion > 0 else 0)
                rubros.append(["Incremento Indemnizatorio Dto. 34/2019", monto_dto34])
                total_historico += monto_dto34
        
        # 6. Días trabajados mes despido
        monto_dias_trabajados = self.calcular_dias_trabajados_mes_despido()
        rubros.append((f"Días trabajados mes despido ({self.despido.day} días)", monto_dias_trabajados))
        total_historico += monto_dias_trabajados

        # SAC Semestre Anterior (opcional)
        sac_ant = self.calcular_sac_semestre_anterior()
        if sac_ant > 0:
            rubros.append(["SAC Semestre Anterior Adeudado", sac_ant])
            total_historico += sac_ant

        # 7. SAC Prop.
        sac_proporcional = self.calcular_sac_prop()
        rubros.append(["SAC Proporcional", sac_proporcional])
        total_historico += sac_proporcional

        # 8. Vacaciones Prop.
        vacaciones_proporcionales, vac_dias = self.calcular_vacaciones_prop()
        rubros.append([f"Vacaciones Prop. ({vac_dias:.2f} días)", vacaciones_proporcionales])
        total_historico += vacaciones_proporcionales

        # 9. SAC s/ vacaciones
        sac_vacaciones = vacaciones_proporcionales / 12
        rubros.append(["SAC s/ vacaciones", sac_vacaciones])
        total_historico += sac_vacaciones

        # 10. Salarios adeudados (Rubros Adicionales Predeterminados s/ la lista del usuario)
        # Separamos los rubros adicionales para mantener el orden solicitado: Salarios adeudados antes que multas
        otros_extras = []
        if self.rubros_adicionales:
            for concepto, monto in self.rubros_adicionales:
                if "Salarios adeudados" in concepto:
                    rubros.append([concepto, float(monto)])
                    total_historico += float(monto)
                else:
                    otros_extras.append([concepto, float(monto)])

        # 11. Art. 1º Ley 25.323
        if self.art1: 
             monto_art1 = monto_245 
             rubros.append(["Art. 1º Ley 25.323", monto_art1])
             total_historico += monto_art1

        # 12. Art. 2º Ley 25.323: 50% de (Antigüedad + Preaviso + Integración)
        if self.art2:
            base_multa = monto_245 + monto_preaviso + monto_integracion
            monto_art2 = base_multa * 0.5
            rubros.append(["Art. 2º Ley 25.323", monto_art2])
            total_historico += monto_art2

        # 13. Art. 80 LCT
        if self.art80:
            monto_art80 = self.sueldo * 3
            rubros.append(["Multa Art. 80 LCT", monto_art80])
            total_historico += monto_art80

        # 14. Art. 8 Ley 24.013 (Relación no registrada)
        if self.art8_24013:
            total_meses = self.antiguedad.years * 12 + self.antiguedad.months
            monto_art8 = (total_meses * self.sueldo) / 4
            rubros.append([f"Multa Art. 8º Ley 24.013 ({total_meses} meses)", monto_art8])
            total_historico += monto_art8

        # 15. Art. 15 Ley 24.013 (Despido tras reclamo)
        if self.art15_24013:
            monto_art15 = monto_245 + monto_preaviso + (monto_preaviso / 12) + monto_integracion + (monto_integracion / 12 if monto_integracion > 0 else 0)
            rubros.append(["Multa Art. 15 Ley 24.013", monto_art15])
            total_historico += monto_art15

        # Resto de rubros adicionales
        for concepto, monto in otros_extras:
            rubros.append([concepto, monto])
            total_historico += monto

        row = 7
        for lab, mon in rubros:
            ws.write(row, 0, lab, fmt_txt); ws.write(row, 1, mon, fmt_mon)
            row += 1

        # Agregar el total histórico al final de los rubros
        ws.write(row, 0, "Subtotal Capital Histórico:", fmt_bold); ws.write(row, 1, total_historico, fmt_int)
        
        capital_neto = total_historico
        if self.pagos_a_cuenta > 0:
            row += 1
            ws.write(row, 0, "Pagos realizados a cuenta (al despido):", fmt_bold); ws.write(row, 1, -self.pagos_a_cuenta, fmt_mon)
            capital_neto = total_historico - self.pagos_a_cuenta
            row += 1
            ws.write(row, 0, "CAPITAL HISTÓRICO NETO (Sujeto a actualización):", fmt_bold); ws.write(row, 1, capital_neto, fmt_int)
        
        row += 2 # Dejar una fila en blanco
        
        ws.write(row, 0, "ACTUALIZACIÓN E INTERESES (Fuente: IPC INDEC)", fmt_tit)
        ws.write(row, 1, "", fmt_tit)
        
        cap_act = 0.0
        int_puro = 0.0
        
        # Actualización por IPC + 3%
        coef = self.ipc_fin / self.ipc_inicio
        cap_act = capital_neto * coef
        
        # Cálculo exacto de días transcurridos
        dias_pasados = max(0, (self.hoy - self.despido).days) + 1
        porcentaje_acumulado = dias_pasados * (0.03 / 365) # 3% anual equivale a 3/365% diario aproximadamente 0.0082191780821918%
        int_puro = cap_act * porcentaje_acumulado

        ws.write(row+1, 0, "Coeficiente IPC INDEC:", fmt_txt); ws.write(row+1, 1, coef, workbook.add_format({'num_format': '0.0000', 'border': 1}))
        ws.write(row+2, 0, "CAPITAL ACTUALIZADO (IPC):", fmt_bold); ws.write(row+2, 1, cap_act, fmt_mon)
        ws.write(row+3, 0, f"Interés Puro (3% anual - {dias_pasados} días - {porcentaje_acumulado*100:.2f}% acumulado):", fmt_txt); ws.write(row+3, 1, int_puro, fmt_mon)
        ws.write(row+5, 0, "TOTAL FINAL (Capital Actualizado + Int. 3%):", fmt_int); ws.write(row+5, 1, cap_act + int_puro, fmt_int)
        ws.write(row+6, 0, "TOPE MÍNIMO (67% s/ Total Actualizado):", fmt_txt); ws.write(row+6, 1, (cap_act + int_puro) * 0.67, fmt_mon)
        
        workbook.close()
        if not buffer:
             print(f"\n>>> ¡LIQUIDACIÓN CREADA CON ÉXITO! <<<")
def obtener_datos_online(fecha_objetivo=None):
    """
    Obtiene datos de la API de Datos Argentina.
    Devuelve el valor del índice IPC INDEC para la fecha despido/liquidación (o el último disponible si es None).
    """
    try:
        url = "https://apis.datos.gob.ar/series/api/series/"
        id_serie = "145.3_INGNACNAL_DICI_M_15" # IPC INDEC Nacional (Base 2016)

        params = {"ids": id_serie, "format": "json", "limit": 5000}
        response = requests.get(url, params=params, timeout=10).json()
        data = response['data']
        
        if fecha_objetivo: # Usamos fecha_objetivo como "fecha objetivo" para IPC
            f_dt = datetime.strptime(fecha_objetivo, "%d/%m/%Y")
            target = f_dt.strftime("%Y-%m-01")
            for entry in data:
                if entry[0] == target: return entry[1], datetime.strptime(entry[0], "%Y-%m-%d").strftime("%d/%m/%Y")
            
            # Fallback: si la fecha_objetivo es más nueva que el último dato disponible, devuelve el último
            last_entry = data[-1]
            last_dt = datetime.strptime(last_entry[0], "%Y-%m-%d")
            if f_dt >= last_dt:
                return last_entry[1], last_dt.strftime("%d/%m/%Y")
            
            # Si es más vieja que el primer dato (muy raro), devuelve el primero
            return data[0][1], datetime.strptime(data[0][0], "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            # Retorna último valor y fecha
            last_entry = data[-1]
            return last_entry[1], datetime.strptime(last_entry[0], "%Y-%m-%d").strftime("%d/%m/%Y")

    except Exception as e:
        print(f"Error API: {e}")
        return None, None

def solicitar_datos():
    print("\n" + "="*45 + "\n  LIQUIDADOR JUDICIAL - IPC INDEC\n" + "="*45)
    car = input("1. Carátula: ")
    ing = input("2. Fecha de ingreso (DD/MM/AAAA): ")
    des = input("3. Fecha de despido (DD/MM/AAAA): ")
    rem = input("4. Mejor Remuneración: ").replace(',', '.')

    print(f"\n--- Conectando a Base de Datos de INDEC ---")
    val_ini_tuple = obtener_datos_online(fecha_objetivo=des)
    val_fin_tuple = obtener_datos_online() # Por defecto CLI trae la última fecha para la liquidación
    
    val_ini = val_ini_tuple[0] if val_ini_tuple else None
    
    if val_ini and val_fin_tuple and val_fin_tuple[0]:
        val_fin, fecha_fin = val_fin_tuple
        print(f"[*] IPC Mes Despido (INDEC): {val_ini}")
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
    
    inc_sac = False
    f_des = datetime.strptime(des, "%d/%m/%Y")
    if f_des.month in (1, 7):
        prompt_sac = "¿Adeuda SAC 1er Semestre?" if f_des.month == 7 else "¿Adeuda SAC 2do Semestre (año anterior)?"
        inc_sac = input(f"{prompt_sac} (S/N): ").upper() == 'S'
    
    a80 = input("¿Aplica Art 80 LCT? (S/N): ").upper() == 'S'
    d34 = input("¿Aplica Dto 34/2019? (S/N): ").upper() == 'S'
    
    return LiquidadorLaboral(car, ing, des, float(rem), art1=a1, art2=a2, ipc_inicio=val_ini, ipc_fin=val_fin, incluir_sac_anterior=inc_sac, art80=a80, dto34=d34, pagos_a_cuenta=0.0)

if __name__ == "__main__":
    try:
        mi_caso = solicitar_datos()
        mi_caso.generar_excel()
    except Exception as e:
        print(f"\n[ERROR] {e}")