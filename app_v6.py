import streamlit as st
import math
import matplotlib.pyplot as plt
import numpy as np
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from fpdf import FPDF

# Page configuration
st.set_page_config(
    page_title="한울생약 UV-C 살균 공정 시뮬레이터 v6.0 (White Light Mode)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Light Theme (Clean White Background)
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background-color: #FFFFFF;
        color: #0F172A;
    }
    .main .block-container {
        padding-top: 2rem;
        background-color: #FFFFFF;
    }
    /* Metric Cards */
    .metric-box {
        background-color: #F8FAFC;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-box p {
        color: #475569;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .metric-box h2 {
        color: #1D4ED8;
        margin: 0;
        font-weight: 700;
    }
    .metric-box h1 {
        margin: 0;
        font-weight: 800;
    }
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #F1F5F9;
        border-right: 1px solid #E2E8F0;
    }
    section[data-testid="stSidebar"] .stMarkdown h1, 
    section[data-testid="stSidebar"] .stMarkdown h2, 
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #0F172A;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ 한울생약 UV-C 살균 공정 실시간 시뮬레이터 v6.0")
st.caption("건조 원단 및 포장재 선(先) 살균 가공 공정 전용 웹 시뮬레이션 모델 (Clean Light Mode)")

# Sidebar for inputs
st.sidebar.header("🛠️ 1. 설비 기하학 및 공정 변수")
y_tunnel = st.sidebar.slider("자외선 살균 터널 길이 (mm)", min_value=500, max_value=5000, value=2000, step=100)
d_gap = st.sidebar.slider("물체와 램프 간 이격 거리 (mm)", min_value=50, max_value=1000, value=200, step=10)
v_speed = st.sidebar.slider("원단 이송 속도 (m/s)", min_value=0.05, max_value=2.0, value=0.3, step=0.05)

st.sidebar.header("💡 2. 자외선 광원(Lamp) 배치 및 출력")
n_lamps = st.sidebar.slider("총 설치 램프 수 (개)", min_value=1, max_value=24, value=6, step=1)
p_lamp = st.sidebar.slider("단일 램프 정격 전력 (W)", min_value=10, max_value=200, value=30, step=5)
eff_uvc = st.sidebar.slider("UVC 변환 효율", min_value=0.1, max_value=0.5, value=0.35, step=0.05)
l_lamp = st.sidebar.slider("유리 램프 유효 발광 길이 (mm)", min_value=100, max_value=2000, value=900, step=50)

st.sidebar.header("🛡️ 3. 생산 현장 감쇄 장벽 손실율")
t_shadow = st.sidebar.slider("그림자 장벽 투과율 (50% 감쇄 = 0.5)", min_value=0.1, max_value=1.0, value=0.5, step=0.05)
t_aging = st.sidebar.slider("램프 노화 및 분진 오염도 (20% 손실 = 0.8)", min_value=0.1, max_value=1.0, value=0.8, step=0.05)

# Fixed lotion loss because of pre-sterilization (T_lotion = 1.0)
t_lotion = 1.0

# 4. 자외선 선량 물리 연산 결과
p_total = n_lamps * p_lamp * eff_uvc * 1000  # mW
t_exp = y_tunnel / (v_speed * 1000)  # seconds

# Keitz line source formula modeling
gap_cm = d_gap / 10.0
length_cm = l_lamp / 10.0
i_peak = p_total / (2 * math.pi * gap_cm * length_cm)  # mW/cm2

# Final valid dose (mJ/cm2)
dose = i_peak * t_exp * t_shadow * t_lotion * t_aging

# Target micro-organisms and requirements
targets = {
    "버크홀데리아 (Burkholderia)": {"limit": 7.4, "surrogate": "Burkholderia pseudomallei"},
    "아세토박터-초산균 (Acetobacter)": {"limit": 10.5, "surrogate": "Brucella suis"},
    "메틸로박테리움 (Methylobacterium)": {"limit": 17.0, "surrogate": "Pseudomonas aeruginosa (녹농균)"}
}

# Excel generation function
def generate_excel_report():
    wb = Workbook()
    ws = wb.active
    ws.title = "UVC살균_성적서"
    ws.views.sheetView[0].showGridLines = True
    
    font_family = "Malgun Gothic"
    title_font = Font(name=font_family, size=14, bold=True, color="1F497D")
    header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
    section_font = Font(name=font_family, size=11, bold=True, color="1F497D")
    normal_font = Font(name=font_family, size=10)
    bold_font = Font(name=font_family, size=10, bold=True)
    
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    sec_fill = PatternFill(start_color="E9EDF4", end_color="E9EDF4", fill_type="solid")
    pass_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    fail_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    ws.merge_cells("A1:D1")
    ws["A1"] = "UVC 살균 공정 유효성 검증 성적서"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[1].height = 25
    
    ws["A3"] = "발급 일시:"
    ws["B3"] = "2026-09-08"
    ws["C3"] = "문서 번호:"
    ws["D3"] = "SOP-UVC-04"
    ws["A4"] = "공정 분류:"
    ws["B4"] = "건조 원단 및 포장재 선(先) 살균 가공 공정"
    
    for r_num in [3, 4]:
        ws[f"A{r_num}"].font = bold_font
        ws[f"B{r_num}"].font = normal_font
        if r_num == 3:
            ws["C3"].font = bold_font
            ws["D3"].font = normal_font
            
    ws["A6"] = "1. 설비 기하학 및 구동 세팅값"
    ws["A6"].font = section_font
    ws.merge_cells("A6:D6")
    for col in range(1, 5):
        ws.cell(row=6, column=col).fill = sec_fill
        
    params = [
        ("살균 터널 길이 (y_tunnel)", f"{y_tunnel} mm", "설치 램프 수 (N_lamps)", f"{n_lamps} 개"),
        ("물체-광원 이격 거리 (d_gap)", f"{d_gap} mm", "단일 램프 정격 전력 (p_lamp)", f"{p_lamp} W"),
        ("원단 이송 속도 (v_speed)", f"{v_speed} m/s", "UVC 변환 효율 (eff_uvc)", f"{eff_uvc*100}%"),
        ("램프 유효 발광 길이 (l_lamp)", f"{l_lamp} mm", "그림자 장벽 투과율 (t_shadow)", f"{t_shadow}"),
        ("램프 노화/오염도 (t_aging)", f"{t_aging}", "로션 함침 감쇄율 (t_lotion)", "1.0 (선살균)")
    ]
    
    curr_row = 7
    for row_data in params:
        ws.cell(row=curr_row, column=1, value=row_data[0]).font = bold_font
        ws.cell(row=curr_row, column=2, value=row_data[1]).font = normal_font
        ws.cell(row=curr_row, column=3, value=row_data[2]).font = bold_font
        ws.cell(row=curr_row, column=4, value=row_data[3]).font = normal_font
        for c in range(1, 5):
            ws.cell(row=curr_row, column=c).border = thin_border
        curr_row += 1
        
    curr_row += 1
    ws.cell(row=curr_row, column=1, value="2. 물리 광학 연산 결과").font = section_font
    ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=4)
    for col in range(1, 5):
        ws.cell(row=curr_row, column=col).fill = sec_fill
        
    curr_row += 1
    results = [
        ("가용 총 UVC 방사출력 (P_total)", f"{p_total:.1f} mW", "조사 노출시간 (t_exp)", f"{t_exp:.3f} 초"),
        ("표면 자외선 최고 조도 (I_peak)", f"{i_peak:.3f} mW/cm²", "최종 유효 자외선 조사량 (Dose)", f"{dose:.2f} mJ/cm²")
    ]
    for row_data in results:
        ws.cell(row=curr_row, column=1, value=row_data[0]).font = bold_font
        ws.cell(row=curr_row, column=2, value=row_data[1]).font = normal_font
        ws.cell(row=curr_row, column=3, value=row_data[2]).font = bold_font
        ws.cell(row=curr_row, column=4, value=row_data[3]).font = normal_font
        if "최종 유효" in row_data[2]:
            ws.cell(row=curr_row, column=4).font = Font(name=font_family, size=10, bold=True, color="1F497D")
        for c in range(1, 5):
            ws.cell(row=curr_row, column=c).border = thin_border
        curr_row += 1
        
    curr_row += 1
    ws.cell(row=curr_row, column=1, value="3. 핵심 타겟 미생물 3종 살균 판정").font = section_font
    ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=4)
    for col in range(1, 5):
        ws.cell(row=curr_row, column=col).fill = sec_fill
        
    curr_row += 1
    headers = ["대상 미생물", "대체 균주", "기준 선량 (mJ/cm²)", "판정 결과"]
    for c_idx, h_text in enumerate(headers, 1):
        cell = ws.cell(row=curr_row, column=c_idx, value=h_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    for name, data in targets.items():
        curr_row += 1
        ws.cell(row=curr_row, column=1, value=name).font = normal_font
        ws.cell(row=curr_row, column=2, value=data["surrogate"]).font = normal_font
        ws.cell(row=curr_row, column=3, value=data["limit"]).font = normal_font
        ws.cell(row=curr_row, column=3).alignment = Alignment(horizontal="center")
        
        is_pass = dose >= data["limit"]
        result_text = "🟢 적합 (PASS)" if is_pass else "🔴 부적합 (FAIL)"
        cell_r = ws.cell(row=curr_row, column=4, value=result_text)
        cell_r.font = bold_font
        cell_r.alignment = Alignment(horizontal="center")
        cell_r.fill = pass_fill if is_pass else fail_fill
        
        for c in range(1, 5):
            ws.cell(row=curr_row, column=c).border = thin_border
            
    curr_row += 2
    ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=4)
    ws.cell(row=curr_row, column=1, value="UVC 살균 공정의 물리적 유효성 검증 결과를 성실히 보고합니다.").font = normal_font
    ws.cell(row=curr_row, column=1).alignment = Alignment(horizontal="center")
    
    curr_row += 1
    ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=4)
    ws.cell(row=curr_row, column=1, value="발급기관: (주)한울생약 기술연구소").font = bold_font
    ws.cell(row=curr_row, column=1).alignment = Alignment(horizontal="center")
    
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
        
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    return excel_file.getvalue()

# PDF generation function
def generate_pdf_report():
    class PDFReport(FPDF):
        def header(self):
            self.set_fill_color(31, 73, 125)
            self.rect(0, 0, 210, 38, "F")
            
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 15)
            self.cell(0, 10, "UVC Process Validation Certificate", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 9)
            self.cell(0, 5, "Hanul Chemical Co., Ltd. - Quality Assurance Dept", align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(12)
            
        def footer(self):
            self.set_y(-15)
            self.set_text_color(128, 128, 128)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")
            
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 7, "Issue Date: 2026-09-08", new_x="RIGHT", new_y="TOP")
    pdf.cell(0, 7, "Doc No: SOP-UVC-04", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, "Process Category: Dry Fabric & Packaging Pre-sterilization Process", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_fill_color(233, 237, 244)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "1. Equipment & Operation Parameters", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    
    col_w = 48
    val_w = 47
    
    params = [
        ("Tunnel Length", f"{y_tunnel} mm", "Total Lamps", f"{n_lamps} ea"),
        ("Distance to Object", f"{d_gap} mm", "Single Lamp Power", f"{p_lamp} W"),
        ("Conveyor Speed", f"{v_speed} m/s", "UVC Conversion Eff.", f"{eff_uvc*100}%"),
        ("Lamp Active Length", f"{l_lamp} mm", "Shadow Transmission", f"{t_shadow}"),
        ("Lamp Aging Factor", f"{t_aging}", "Lotion Loss Factor", "1.0 (Excluded)")
    ]
    
    for p in params:
        pdf.cell(col_w, 7, p[0], border=1)
        pdf.cell(val_w, 7, p[1], border=1)
        pdf.cell(col_w, 7, p[2], border=1)
        pdf.cell(val_w, 7, p[3], border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "2. Physical & Optical Calculation", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    
    pdf.cell(col_w, 7, "Total UVC Output", border=1)
    pdf.cell(val_w, 7, f"{p_total:.1f} mW", border=1)
    pdf.cell(col_w, 7, "Exposure Duration", border=1)
    pdf.cell(val_w, 7, f"{t_exp:.3f} sec", border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(col_w, 7, "Peak Intensity", border=1)
    pdf.cell(val_w, 7, f"{i_peak:.3f} mW/cm2", border=1)
    pdf.cell(col_w, 7, "Effective UVC Dose", border=1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(val_w, 7, f"{dose:.2f} mJ/cm2", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "3. Micro-organism Inactivation Evaluation", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_fill_color(31, 73, 125)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(50, 8, "Target Micro-organism", border=1, fill=True, align="C")
    pdf.cell(55, 8, "Surrogate Strain", border=1, fill=True, align="C")
    pdf.cell(40, 8, "Limit (mJ/cm2)", border=1, fill=True, align="C")
    pdf.cell(45, 8, "Evaluation Result", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    
    eng_names = {
        "버크홀데리아 (Burkholderia)": "Burkholderia",
        "아세토박터-초산균 (Acetobacter)": "Acetobacter",
        "메틸로박테리움 (Methylobacterium)": "Methylobacterium"
    }
    
    for name, data in targets.items():
        is_pass = dose >= data["limit"]
        result_text = "PASS" if is_pass else "FAIL"
        
        pdf.cell(50, 8, eng_names.get(name, name), border=1)
        pdf.cell(55, 8, data["surrogate"], border=1)
        pdf.cell(40, 8, f"{data['limit']:.1f}", border=1, align="C")
        
        if is_pass:
            pdf.set_fill_color(226, 239, 218)
            pdf.set_text_color(46, 117, 89)
        else:
            pdf.set_fill_color(252, 228, 214)
            pdf.set_text_color(192, 0, 0)
            
        pdf.cell(45, 8, result_text, border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        
    pdf.ln(12)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Hanul Chemical Co., Ltd. Technology Research Institute", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, "This is an official computational verification statement based on FDA 21 CFR & EPA FIFRA standards.", align="C", new_x="LMARGIN", new_y="NEXT")
    
    return bytes(pdf.output())

# Main Layout: 2 Columns
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 실시간 광학 연산 결과")
    
    st.markdown(f"""
    <div style="display: flex; justify-content: space-around; margin-bottom: 20px;">
        <div class="metric-box" style="flex: 1; margin: 5px;">
            <p style="color: #475569; margin-bottom: 5px; font-weight: 600;">가용 총 UVC 방사출력</p>
            <h2 style="color: #1D4ED8; margin: 0; font-size: 26px;">{p_total:.1f} mW</h2>
        </div>
        <div class="metric-box" style="flex: 1; margin: 5px;">
            <p style="color: #475569; margin-bottom: 5px; font-weight: 600;">조사 노출시간</p>
            <h2 style="color: #1D4ED8; margin: 0; font-size: 26px;">{t_exp:.3f} 초</h2>
        </div>
    </div>
    <div style="display: flex; justify-content: space-around; margin-bottom: 20px;">
        <div class="metric-box" style="flex: 1; margin: 5px;">
            <p style="color: #475569; margin-bottom: 5px; font-weight: 600;">표면 자외선 최고 조도</p>
            <h2 style="color: #D97706; margin: 0; font-size: 26px;">{i_peak:.3f} mW/cm²</h2>
        </div>
        <div class="metric-box" style="flex: 1; margin: 5px; border: 2px solid #16A34A; background-color: #F0FDF4;">
            <p style="color: #15803D; font-weight: bold; margin-bottom: 5px;">최종 유효 자외선 조사량 (Dose)</p>
            <h1 style="color: #15803D; margin: 0; font-size: 32px;">{dose:.2f} mJ/cm²</h1>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("🚨 핵심 타겟 미생물 3종 살균 합불(PASS/FAIL) 진단")
    for name, data in targets.items():
        limit = data["limit"]
        is_pass = dose >= limit
        status_text = "🟢 적합 (PASS)" if is_pass else "🔴 부적합 (FAIL)"
        status_color = "#16A34A" if is_pass else "#DC2626"
        card_bg = "#F0FDF4" if is_pass else "#FEF2F2"
        
        st.markdown(f"""
        <div style="background-color: {card_bg}; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; border-left: 5px solid {status_color}; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="margin: 0; color: #0F172A; font-weight: 700;">{name}</h4>
                    <p style="margin: 0; font-size: 13px; color: #64748B;">대체 균주: {data['surrogate']}</p>
                </div>
                <div style="text-align: right;">
                    <span style="font-weight: bold; color: {status_color}; font-size: 18px;">{status_text}</span>
                    <p style="margin: 0; font-size: 12px; color: #475569; font-weight: 600;">기준: {limit} mJ/cm²</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # General margin and status
    margin_ratio = dose / 17.0
    margin_status = "🟢 안전 마진 충분 (PASS)" if margin_ratio >= 1.0 else "🔴 안전선 미달 (FAIL)"
    margin_color = "#16A34A" if margin_ratio >= 1.0 else "#DC2626"
    box_bg = "#F0FDF4" if margin_ratio >= 1.0 else "#FEF2F2"
    
    st.markdown(f"""
    <div style="background-color: {box_bg}; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid {margin_color}; margin-top: 15px;">
        <span style="color: #334155; font-size: 14px; font-weight: 600;">종합 공정 안전 마진 배수: </span>
        <strong style="color: #0F172A; font-size: 22px;">{margin_ratio:.2f} 배</strong>
        <h3 style="color: {margin_color}; margin: 5px 0 0 0; font-weight: 700;">{margin_status}</h3>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.subheader("📈 Operating Point Tracking Graph")
    
    speeds = np.linspace(0.05, 2.0, 100)
    doses = [i_peak * (y_tunnel / (s * 1000)) * t_shadow * t_lotion * t_aging for s in speeds]
    
    fig, ax = plt.subplots(figsize=(6, 4.5))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')
    
    ax.plot(speeds, doses, color='#2563EB', label='UVC Dose by Speed', linewidth=2.5)
    ax.scatter([v_speed], [dose], color='#16A34A', s=160, zorder=5, label='Current Operating Point', edgecolor='#065F46', linewidth=1.5)
    
    ax.axhline(y=17.0, color='#DC2626', linestyle='--', alpha=0.8, label='Methylobacterium Limit (17.0 mJ/cm²)')
    ax.axhline(y=10.5, color='#D97706', linestyle='--', alpha=0.8, label='Acetobacter Limit (10.5 mJ/cm²)')
    ax.axhline(y=7.4, color='#0284C7', linestyle='--', alpha=0.8, label='Burkholderia Limit (7.4 mJ/cm²)')
    
    ax.set_xlabel('Conveyor Speed (m/s)', color='#0F172A', fontsize=10, fontweight='bold')
    ax.set_ylabel('UVC Effective Dose (mJ/cm²)', color='#0F172A', fontsize=10, fontweight='bold')
    ax.set_title('Real-time Operating Point Tracking', color='#0F172A', fontsize=12, fontweight='bold')
    
    ax.tick_params(colors='#334155')
    for spine in ax.spines.values():
        spine.set_color('#CBD5E1')
        
    ax.legend(facecolor='#FFFFFF', edgecolor='#CBD5E1', labelcolor='#0F172A', loc='upper right', fontsize=8)
    ax.grid(True, color='#E2E8F0', linestyle=':', alpha=0.8)
    ax.set_ylim(0, max(100, dose * 1.5))
    
    st.pyplot(fig)
    
    st.subheader("📄 공정 성적서 및 검증 보고서 발급")
    
    excel_bytes = generate_excel_report()
    pdf_bytes = generate_pdf_report()
    
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.download_button(
            label="📥 엑셀 형식 성적서 다운로드 (.xlsx)",
            data=excel_bytes,
            file_name="hanul-uvc-validation-report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with d_col2:
        st.download_button(
            label="📥 PDF 형식 보고서 다운로드 (.pdf)",
            data=pdf_bytes,
            file_name="hanul-uvc-validation-report.pdf",
            mime="application/pdf"
        )

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748B; font-size: 12px;'>본 프로그램은 한울생약 연구소의 자외선 살균 수립 보고서와 동일한 물리적 연산 수식으로 작동합니다. | Source: FDA 21 CFR & EPA FIFRA</p>", unsafe_allow_html=True)
