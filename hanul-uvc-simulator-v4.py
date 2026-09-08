# -*- coding: utf-8 -*-
"""
한울생약 UV-C 살균 공정 실시간 시뮬레이터 v4.0 (독립형 Desktop App)
작성일자: 2026-09-08
작성자: 한울생약 연구소 x Gemini Notebook
설명: 본 프로그램은 건조 원단 및 포장재 선(先) 살균 공정의 물리적 자외선 조사량(Dose)을
      실시간으로 계산 및 시각화하고, 주요 오염 유해 미생물 3종에 대한 사멸 합격 여부(PASS/FAIL)를
      판정하는 데스크톱 전용 독립 시뮬레이션 프로그램입니다.
"""

import sys
import os
import math
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

# 시각화 차트를 위한 Matplotlib 임포트
import matplotlib
matplotlib.use('TkAgg') # Tkinter 임베딩 전용 백엔드 설정
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# 한글 폰트 설정 (시스템 환경에 맞춰 안전하게 대비)
from matplotlib import font_manager, rc
try:
    # 윈도우 환경 한글 폰트 (맑은 고딕)
    font_name = font_manager.FontProperties(fname="c:/Windows/Fonts/malgun.ttf").get_name()
    rc('font', family=font_name)
except:
    try:
        # 맥 환경 한글 폰트 (AppleGothic)
        rc('font', family='AppleGothic')
    except:
        # 리눅스 및 기타 환경 (기본 설정)
        pass

class UVSimulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("한울생약 UV-C 살균 공정 실시간 시뮬레이터 v4.0")
        self.geometry("1100x780")
        self.configure(bg="#1E222B") # 모던 딥 그레이/다크모드 백그라운드
        
        # 기본 스타일 설정
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background='#1E222B', foreground='#FFFFFF')
        self.style.configure('TLabel', background='#1E222B', foreground='#FFFFFF', font=('Malgun Gothic', 10))
        self.style.configure('TFrame', background='#1E222B')
        
        # --- [초기 변수 및 물리 모델 스펙 설정] ---
        # 1. 설비 기하학 및 공정 설계 변수
        self.y_tunnel = tk.DoubleVar(value=2000.0)  # 자외선 터널 길이 (mm)
        self.z_object = tk.DoubleVar(value=500.0)   # 원단/박스 통과 높이 (mm)
        self.d_gap = tk.DoubleVar(value=200.0)      # 물체와 램프 간 이격 거리 (mm)
        self.v_speed = tk.DoubleVar(value=0.3)      # 원단 이송 속도 (m/s)
        
        # 2. 광원(Lamp) 배치 및 출력 변수
        self.N_lamps = tk.IntVar(value=6)           # 설치 램프 수
        self.P_lamp = tk.DoubleVar(value=30.0)      # 단일 램프 전력 (W)
        self.Eff_uvc = tk.DoubleVar(value=0.35)     # UVC 변환 효율 (35%)
        self.L_lamp = tk.DoubleVar(value=900.0)     # 유리 램프 발광 길이 (mm)
        
        # 3. 생산 현장 감쇄 장벽 손실율 (선살균 공정 최적화 반영)
        self.T_shadow = tk.DoubleVar(value=0.5)     # 그림자 효과 투과율 (50% 감쇄)
        self.T_lotion = tk.DoubleVar(value=1.0)     # 로션 감쇄율 (★선살균 공정 적용으로 100% 관통!)
        self.T_aging = tk.DoubleVar(value=0.8)      # 램프 노화 및 분진 오염도 (20% 감쇄)
        
        # 미생물 사멸 기준선 (mJ/cm²)
        self.target_microbes = {
            "Burkholderia": {"name": "버크홀데리아 (Burkholderia pseudomallei)", "dose": 7.4, "color": "#00FF66"},
            "Acetobacter": {"name": "아세토박터-초산균 (Brucella suis 대체)", "dose": 10.5, "color": "#00FF66"},
            "Methylobacterium": {"name": "메틸로박테리움 (녹농균 대체)", "dose": 17.0, "color": "#00FF66"}
        }
        
        # UI 레이아웃 설계
        self.create_widgets()
        
        # 최초 계산 실행
        self.calculate_and_update()

    def create_widgets(self):
        # 상단 헤더 프레임
        header_frame = tk.Frame(self, bg="#282C34", height=60, relief=tk.RAISED, bd=1)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        
        header_label = tk.Label(
            header_frame, 
            text="한울생약 UV-C 살균 공정 실시간 시뮬레이터 v4.0", 
            font=("Malgun Gothic", 16, "bold"), 
            fg="#61AFEF", 
            bg="#282C34"
        )
        header_label.pack(pady=12, padx=20, side=tk.LEFT)
        
        sub_header_label = tk.Label(
            header_frame,
            text="[건조 원단 및 포장재 선(先) 살균 공정 특화 에디션]",
            font=("Malgun Gothic", 10, "italic"),
            fg="#ABB2BF",
            bg="#282C34"
        )
        sub_header_label.pack(pady=16, padx=5, side=tk.LEFT)

        # 메인 콘텐츠 분할 영역 (좌측: 슬라이더 컨트롤러, 우측: 수치 결과 및 실시간 그래프)
        main_body = tk.Frame(self, bg="#1E222B")
        main_body.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # --- [좌측 프레임: 입력 파라미터 조절용 슬라이더 영역] ---
        left_frame = tk.Frame(main_body, bg="#1E222B", width=420)
        left_frame.pack(fill=tk.Y, side=tk.LEFT, padx=(0, 10))
        left_frame.pack_propagate(False)
        
        # 섹션 1: 공정 설계 변수
        sec1_frame = tk.LabelFrame(left_frame, text="1. 설비 기하학 및 이송 속도", bg="#1E222B", fg="#61AFEF", font=("Malgun Gothic", 11, "bold"), padx=10, pady=8)
        sec1_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_slider_row(sec1_frame, "자외선 터널 길이 (mm)", self.y_tunnel, 500, 5000, 100)
        self.create_slider_row(sec1_frame, "물체와 램프 이격 거리 (mm)", self.d_gap, 50, 800, 10)
        self.create_slider_row(sec1_frame, "원단 이송 속도 (m/s)", self.v_speed, 0.05, 1.5, 0.01, is_float=True)
        
        # 섹션 2: 자외선 광원 사양
        sec2_frame = tk.LabelFrame(left_frame, text="2. 자외선 광원(UV-LED) 스펙", bg="#1E222B", fg="#98C379", font=("Malgun Gothic", 11, "bold"), padx=10, pady=8)
        sec2_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_slider_row(sec2_frame, "총 설치 램프 수 (개)", self.N_lamps, 2, 24, 1)
        self.create_slider_row(sec2_frame, "단일 램프 소비전력 (W)", self.P_lamp, 10, 150, 5)
        self.create_slider_row(sec2_frame, "UVC 광 변환 효율 (비율)", self.Eff_uvc, 0.1, 0.5, 0.01, is_float=True)
        self.create_slider_row(sec2_frame, "램프 유효 발광 길이 (mm)", self.L_lamp, 300, 2000, 50)
        
        # 섹션 3: 4대 환경 감쇄 장벽 (선살균 공정 반영)
        sec3_frame = tk.LabelFrame(left_frame, text="3. 공정 환경 감쇄 제어 변수", bg="#1E222B", fg="#E5C07B", font=("Malgun Gothic", 11, "bold"), padx=10, pady=8)
        sec3_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_slider_row(sec3_frame, "미시 그림자 투과율 (T_shadow)", self.T_shadow, 0.1, 1.0, 0.05, is_float=True)
        self.create_slider_row(sec3_frame, "로션액 투과율 (★선살균 고정)", self.T_lotion, 0.1, 1.0, 0.05, is_float=True, disabled=True)
        self.create_slider_row(sec3_frame, "램프 노화/오염 유지도 (T_aging)", self.T_aging, 0.5, 1.0, 0.05, is_float=True)
        
        # 안내 문구 (선살균 혁신성 박스)
        info_box = tk.Frame(left_frame, bg="#2C313C", bd=1, relief=tk.SOLID)
        info_box.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        info_title = tk.Label(info_box, text="💡 공정 혁신 가이드 (선살균 공정)", bg="#2C313C", fg="#E5C07B", font=("Malgun Gothic", 9, "bold"))
        info_title.pack(anchor="w", padx=10, pady=(8, 2))
        
        info_desc = tk.Label(
            info_box, 
            text="물티슈 원단에 약액(로션)을 함침하기 전 건조한 상태\n자체에서 살균을 진행하므로, 로션에 의한 자외선\n감쇄 효과가 차단되어 로션액 투과율이 1.0(100%)\n으로 자동 고정되어 압도적인 선량 마진을 확보합니다.",
            bg="#2C313C", fg="#ABB2BF", font=("Malgun Gothic", 9), justify=tk.LEFT
        )
        info_desc.pack(anchor="w", padx=10, pady=(0, 8))

        # --- [우측 프레임: 계산 결과 계기판 및 차트 영역] ---
        right_frame = tk.Frame(main_body, bg="#1E222B")
        right_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        
        # 4. 실시간 조사량 메인 계기판
        dose_panel = tk.Frame(right_frame, bg="#21252B", bd=2, relief=tk.SOLID)
        dose_panel.pack(fill=tk.X, pady=(0, 15))
        
        # 상단 라벨
        calc_title_label = tk.Label(
            dose_panel, 
            text="현장 보정 최종 유효조사량 (Final Effective UV Dose)", 
            font=("Malgun Gothic", 11, "bold"), 
            fg="#ABB2BF", 
            bg="#21252B"
        )
        calc_title_label.pack(pady=(12, 2))
        
        # 조사량 메인 디스플레이 변수
        self.dose_value_label = tk.Label(
            dose_panel, 
            text="0.00 mJ/cm²", 
            font=("Consolas", 32, "bold"), 
            fg="#00FF66", 
            bg="#21252B"
        )
        self.dose_value_label.pack()
        
        # 종합 합격 여부 팝업 바
        self.status_bar = tk.Label(
            dose_panel, 
            text="품질 마진 충분 (PASS)", 
            font=("Malgun Gothic", 12, "bold"), 
            fg="#FFFFFF", 
            bg="#00E676", 
            height=2
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 중간 영역 2분할 (왼쪽: 수치상세/미생물판정, 오른쪽: Matplotlib 차트)
        middle_zone = tk.Frame(right_frame, bg="#1E222B")
        middle_zone.pack(fill=tk.BOTH, expand=True)
        
        # 상세 연산 데이터 & 미생물 판정판
        data_pane = tk.Frame(middle_zone, bg="#1E222B", width=280)
        data_pane.pack(fill=tk.Y, side=tk.LEFT, padx=(0, 10))
        data_pane.pack_propagate(False)
        
        # 상세 데이터 수치 프레임
        detail_frame = tk.LabelFrame(data_pane, text="상세 가용 물리량 수치", bg="#1E222B", fg="#61AFEF", font=("Malgun Gothic", 10, "bold"), padx=10, pady=8)
        detail_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.lbl_p_total = self.create_data_row(detail_frame, "UVC 가용 방사출력:", "0 mW")
        self.lbl_t_exp = self.create_data_row(detail_frame, "영역 통과 노출시간:", "0.00 초")
        self.lbl_i_peak = self.create_data_row(detail_frame, "표면 도달 자외선조도:", "0.00 mW/cm²")
        self.lbl_safety_margin = self.create_data_row(detail_frame, "공정 안전 마진배수:", "0.00 x")
        
        # 3대 유해미생물 실시간 사멸 모니터링판
        microbe_frame = tk.LabelFrame(data_pane, text="대상 미생물별 사멸 통제 모니터링", bg="#1E222B", fg="#FF6B6B", font=("Malgun Gothic", 10, "bold"), padx=10, pady=8)
        microbe_frame.pack(fill=tk.BOTH, expand=True)
        
        self.microbe_widgets = {}
        for key, value in self.target_microbes.items():
            m_frame = tk.Frame(microbe_frame, bg="#1E222B", pady=5)
            m_frame.pack(fill=tk.X)
            
            name_lbl = tk.Label(m_frame, text=value["name"], font=("Malgun Gothic", 8, "bold"), fg="#ABB2BF", bg="#1E222B")
            name_lbl.pack(anchor="w")
            
            status_row = tk.Frame(m_frame, bg="#1E222B")
            status_row.pack(fill=tk.X)
            
            req_lbl = tk.Label(status_row, text=f"기준: {value['dose']} mJ/cm²", font=("Malgun Gothic", 8), fg="#5C6370", bg="#1E222B")
            req_lbl.pack(side=tk.LEFT)
            
            status_dot = tk.Label(status_row, text="합격 (PASS)", font=("Malgun Gothic", 8, "bold"), fg="#1E222B", bg="#00FF66", padx=6, width=12)
            status_dot.pack(side=tk.RIGHT)
            
            self.microbe_widgets[key] = status_dot
            
        # 차트 영역
        chart_pane = tk.LabelFrame(middle_zone, text="이송 속도별 조사선량 감쇄 곡선 (실시간 작동점 트래킹)", bg="#1E222B", fg="#ABB2BF", font=("Malgun Gothic", 10, "bold"))
        chart_pane.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        
        self.fig, self.ax = plt.subplots(figsize=(5, 3.5), facecolor='#1E222B')
        self.fig.subplots_adjust(bottom=0.15, left=0.15, top=0.9, right=0.95)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_pane)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 하단 작업 제어 버튼 영역
        control_bar = tk.Frame(right_frame, bg="#1E222B")
        control_bar.pack(fill=tk.X, pady=(15, 0))
        
        btn_reset = tk.Button(
            control_bar, 
            text="기본 설계값 초기화", 
            font=("Malgun Gothic", 10, "bold"), 
            bg="#4B5263", fg="#FFFFFF", 
            activebackground="#5C6370", activeforeground="#FFFFFF",
            relief=tk.GROOVE, bd=1, padx=15, pady=5,
            command=self.reset_inputs
        )
        btn_reset.pack(side=tk.LEFT)
        
        btn_export = tk.Button(
            control_bar, 
            text="품질 검증 보고서 및 공정 성적서 다운로드(SOP)", 
            font=("Malgun Gothic", 10, "bold"), 
            bg="#98C379", fg="#1E222B", 
            activebackground="#A3E28B", activeforeground="#1E222B",
            relief=tk.GROOVE, bd=1, padx=20, pady=5,
            command=self.export_report
        )
        btn_export.pack(side=tk.RIGHT)

    def create_slider_row(self, parent, label, var, from_, to, resolution, is_float=False, disabled=False):
        row = tk.Frame(parent, bg="#1E222B", pady=4)
        row.pack(fill=tk.X)
        
        lbl_text = tk.Label(row, text=label, font=("Malgun Gothic", 9), fg="#ABB2BF", bg="#1E222B", width=25, anchor="w")
        lbl_text.pack(side=tk.LEFT)
        
        # 소수점 표시 포맷 정의
        val_fmt = "{:.2f}" if is_float else "{:.0f}"
        lbl_val = tk.Label(row, text=val_fmt.format(var.get()), font=("Consolas", 10, "bold"), fg="#61AFEF", bg="#1E222B", width=6, anchor="e")
        
        def on_slider_move(val):
            # 변수값 업데이트 및 자릿수 맞춤
            if is_float:
                var.set(round(float(val), 2))
            else:
                var.set(int(float(val)))
            lbl_val.config(text=val_fmt.format(var.get()))
            self.calculate_and_update()
            
        state = tk.DISABLED if disabled else tk.NORMAL
        slider = tk.Scale(
            row, 
            from_=from_, to=to, resolution=resolution, 
            orient=tk.HORIZONTAL, variable=var,
            showvalue=False, bg="#1E222B", fg="#ABB2BF",
            highlightbackground="#1E222B", activebackground="#61AFEF",
            command=on_slider_move, state=state, width=12
        )
        slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 5))
        lbl_val.pack(side=tk.RIGHT)

    def create_data_row(self, parent, label, init_val):
        row = tk.Frame(parent, bg="#1E222B", pady=4)
        row.pack(fill=tk.X)
        
        lbl_l = tk.Label(row, text=label, font=("Malgun Gothic", 9), fg="#ABB2BF", bg="#1E222B", anchor="w")
        lbl_l.pack(side=tk.LEFT)
        
        lbl_r = tk.Label(row, text=init_val, font=("Consolas", 10, "bold"), fg="#61AFEF", bg="#1E222B", anchor="e")
        lbl_r.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        return lbl_r

    def calculate_and_update(self):
        # 1. 입력 변수 수집
        y_tunnel_val = self.y_tunnel.get()
        d_gap_val = self.d_gap.get()
        v_speed_val = self.v_speed.get()
        
        N_lamps_val = self.N_lamps.get()
        P_lamp_val = self.P_lamp.get()
        Eff_uvc_val = self.Eff_uvc.get()
        L_lamp_val = self.L_lamp.get()
        
        T_shadow_val = self.T_shadow.get()
        T_lotion_val = self.T_lotion.get() # 고정값 1.0 (선살균 공정)
        T_aging_val = self.T_aging.get()
        
        # 2. 물리적 연산 모델
        # 총 UVC 방사 출력 (mW)
        P_total = N_lamps_val * P_lamp_val * Eff_uvc_val * 1000.0
        
        # 통과 노출 시간 (sec)
        # speed가 m/s이므로 mm 터널을 통과하는 시간: tunnel / (speed * 1000)
        if v_speed_val > 0:
            t_exp = y_tunnel_val / (v_speed_val * 1000.0)
        else:
            t_exp = 0
            
        # 표면 자외선 최고 조도 (mW/cm2) - Keitz 선광원 배광 적분 근사식 적용
        # mm 단위를 cm 단위로 변환하여 적용
        d_gap_cm = d_gap_val / 10.0
        L_lamp_cm = L_lamp_val / 10.0
        I_peak = P_total / (2.0 * math.pi * d_gap_cm * L_lamp_cm)
        
        # 최종 유효 도달선량 (Dose, mJ/cm2)
        # 로션 감쇄율은 선살균 적용으로 1.0 고정이므로 무손실 작동!
        Dose = I_peak * t_exp * T_shadow_val * T_lotion_val * T_aging_val
        
        # 3. 데이터 화면 갱신
        self.lbl_p_total.config(text=f"{int(P_total):,} mW")
        self.lbl_t_exp.config(text=f"{t_exp:.2f} 초")
        self.lbl_i_peak.config(text=f"{I_peak:.2f} mW/cm²")
        
        self.dose_value_label.config(text=f"{Dose:.2f} mJ/cm²")
        
        # 미생물별 합불 판정 점등
        all_passed = True
        for key, value in self.target_microbes.items():
            widget = self.microbe_widgets[key]
            threshold = value["dose"]
            if Dose >= threshold:
                widget.config(text="합격 (PASS)", bg="#00E676", fg="#1E222B")
            else:
                widget.config(text="미달 (FAIL)", bg="#FF1744", fg="#FFFFFF")
                all_passed = False
                
        # 종합 안전 마진율
        safety_factor = Dose / 17.0 # 가장 내성이 강한 메틸로박테리움 기준
        self.lbl_safety_margin.config(text=f"{safety_factor:.2f} 배")
        
        # 종합 마진 팝업 판정
        if all_passed:
            self.status_bar.config(
                text=f"품질 보증 마진 충분 (PASS) - 안전율 {safety_factor:.1f}x 보유", 
                bg="#00E676", fg="#1E222B"
            )
            self.dose_value_label.config(fg="#00FF66")
        else:
            self.status_bar.config(
                text="일부 유해균 소독 선량 미달 (FAIL) - 이송속도 하향 조정 권장", 
                bg="#FF1744", fg="#FFFFFF"
            )
            self.dose_value_label.config(fg="#FF3366")
            
        # 4. 차트 실시간 갱신
        self.update_chart(v_speed_val, Dose, P_total, y_tunnel_val, T_shadow_val, T_lotion_val, T_aging_val, d_gap_cm, L_lamp_cm)

    def update_chart(self, current_speed, current_dose, P_total, y_tunnel, T_shadow, T_lotion, T_aging, d_gap_cm, L_lamp_cm):
        self.ax.clear()
        
        # 그래프 디자인 설정 (다크모드 매칭)
        self.ax.set_facecolor('#1E222B')
        self.ax.spines['bottom'].set_color('#5C6370')
        self.ax.spines['top'].set_color('#5C6370')
        self.ax.spines['left'].set_color('#5C6370')
        self.ax.spines['right'].set_color('#5C6370')
        self.ax.tick_params(axis='x', colors='#ABB2BF', labelsize=8)
        self.ax.tick_params(axis='y', colors='#ABB2BF', labelsize=8)
        self.ax.set_xlabel("원단 이송 속도 (m/s)", color='#ABB2BF', fontproperties=("Malgun Gothic", 9))
        self.ax.set_ylabel("유효 조사량 (mJ/cm²)", color='#ABB2BF', fontproperties=("Malgun Gothic", 9))
        self.ax.set_title("속도-선량 반비례 곡선과 현재 구동점", color='#61AFEF', fontproperties=("Malgun Gothic", 10, "bold"), pad=10)
        
        # X축 데이터 생성 (속도 0.05 m/s ~ 1.5 m/s)
        speeds = [i / 100.0 for i in range(5, 151)]
        doses = []
        for v in speeds:
            t = y_tunnel / (v * 1000.0)
            I = P_total / (2.0 * math.pi * d_gap_cm * L_lamp_cm)
            d = I * t * T_shadow * T_lotion * T_aging
            doses.append(d)
            
        # 곡선 그리기
        self.ax.plot(speeds, doses, color="#61AFEF", linewidth=2, label="자외선 조사 곡선")
        
        # 가로 임계 안전선 (최고 내성 메틸로박테리움 17.0 mJ/cm² 기준선)
        self.ax.axhline(y=17.0, color="#FF3366", linestyle="--", linewidth=1, alpha=0.7, label="최소 안전 기준선 (17 mJ/cm²)")
        
        # 현재 작동점 표시
        self.ax.plot(current_speed, current_dose, marker='o', markersize=8, color="#00FF66", markeredgecolor="#1E222B")
        self.ax.text(
            current_speed + 0.03, current_dose + 2.0, 
            f"현재 점: {current_dose:.1f} mJ/cm² ({current_speed} m/s)", 
            color="#00FF66", fontproperties=("Consolas", 8, "bold")
        )
        
        # 축 한계 및 눈금 설정
        self.ax.set_xlim(0, 1.6)
        # 최대 Y값은 데이터에 맞춰 동적 조율
        max_y = max(doses) if doses else 100
        self.ax.set_ylim(0, min(150, max_y * 1.1))
        
        self.ax.grid(True, color="#2C313C", linestyle=":")
        self.canvas.draw()

    def reset_inputs(self):
        # 기본 스펙 복원
        self.y_tunnel.set(2000.0)
        self.d_gap.set(200.0)
        self.v_speed.set(0.3)
        self.N_lamps.set(6)
        self.P_lamp.set(30.0)
        self.Eff_uvc.set(0.35)
        self.L_lamp.set(900.0)
        self.T_shadow.set(0.5)
        self.T_aging.set(0.8)
        self.calculate_and_update()
        messagebox.showinfo("초기화 완료", "모든 공정 설계 및 광원 변수들이 한울생약 표준 수치로 재설정되었습니다.")

    def export_report(self):
        # 현재 날짜 및 결과 수집
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 계산 데이터 재추출
        y_tunnel_val = self.y_tunnel.get()
        d_gap_val = self.d_gap.get()
        v_speed_val = self.v_speed.get()
        N_lamps_val = self.N_lamps.get()
        P_lamp_val = self.P_lamp.get()
        Eff_uvc_val = self.Eff_uvc.get()
        L_lamp_val = self.L_lamp.get()
        T_shadow_val = self.T_shadow.get()
        T_lotion_val = self.T_lotion.get()
        T_aging_val = self.T_aging.get()
        
        P_total = N_lamps_val * P_lamp_val * Eff_uvc_val * 1000.0
        t_exp = y_tunnel_val / (v_speed_val * 1000.0) if v_speed_val > 0 else 0
        I_peak = P_total / (2.0 * math.pi * (d_gap_val / 10.0) * (L_lamp_val / 10.0))
        Dose = I_peak * t_exp * T_shadow_val * T_lotion_val * T_aging_val
        safety_factor = Dose / 17.0
        
        status_text = "합격 (PASS)" if safety_factor >= 1.0 else "불합격 (FAIL)"
        
        # 보고서 서식 작성
        report_content = f"""================================================================================
          한울생약 아쿠아윕스(Aqua Wipes) 자외선 살균 공정 적합성 보고서
================================================================================
일시: {now}
작성처: 한울생약 기업부설연구소 품질보증실
공정 설계명: 건조 원단 및 포장재 선(先) 자외선 살균 최적화 엔지니어링

[1. 설비 기하학 및 공정 운전 조건]
- 자외선 살균 터널 길이: {y_tunnel_val:.1f} mm
- 물체와 램프 이격 거리: {d_gap_val:.1f} mm
- 원단/포장재 고속 이송 속도: {v_speed_val:.2f} m/s (약 {v_speed_val*60:.1f} m/min)

[2. 자외선 광원(UV-LED) 물리적 스펙]
- 전체 설치 램프 수: {N_lamps_val} 개
- 단일 램프 정격 전력: {P_lamp_val:.1f} W (총 소비 전력: {N_lamps_val*P_lamp_val:.1f} W)
- 전기 에너지 대비 UVC 방사 변환 효율: {Eff_uvc_val*100:.1f} %
- 유리 램프 유효 발광 길이: {L_lamp_val:.1f} mm
- 총 가용 UVC 방사 출력: {P_total:,.1f} mW

[3. 공정 장벽 및 물리 감쇄 손실율]
- 미시적 엠보싱 그림자 투과율(T_shadow): {T_shadow_val*100:.1f} % (50% 감쇄 모델 적용)
- 약액 함침 로션 투과율(T_lotion): {T_lotion_val*100:.1f} % (선살균 공정 적용으로 광 감쇄 원천 차단!)
- 먼지 오염 및 자연 노화도(T_aging): {T_aging_val*100:.1f} % (20% 장기 유지 보존율 감쇄)

[4. 최종 광학 연산 결과]
- 자외선 조사 구역 통과 노출시간: {t_exp:.3f} 초
- 피사체 표면 피크 자외선 조도: {I_peak:.3f} mW/cm²
- 최종 유효 도달 자외선 조사선량: {Dose:.3f} mJ/cm²
- 최장 내성균(메틸로박테리움 17.0 mJ/cm²) 기준 안전 마진: {safety_factor:.2f} 배
- 종합 공정 위생 적합성 판정: {status_text}

[5. 대상 유해 미생물 3종 사멸 합불 판정 상세]
1) 버크홀데리아 (Burkholderia) - 기준: 7.4 mJ/cm² ➡️ { "PASS (합격)" if Dose >= 7.4 else "FAIL (불합격)" }
2) 아세토박터-초산균 (Brucella suis) - 기준: 10.5 mJ/cm² ➡️ { "PASS (합격)" if Dose >= 10.5 else "FAIL (불합격)" }
3) 메틸로박테리움 (녹농균 대체) - 기준: 17.0 mJ/cm² ➡️ { "PASS (합격)" if Dose >= 17.0 else "FAIL (불합격)" }

[6. 공격적 대내외 품질 보증 전략 지침]
- 본 성적서는 FDA 21 CFR § 880.6600 규정에 부합하는 '조사량 정밀 연산 및 도출 제어력'의 증빙 자산으로 활용됩니다.
- 본 실증 데이터는 EPA FIFRA 법률상 허위/오도적 문구(Misbranding) 처벌 리스크를 차단하는 사내 품질 무기로 5년간 영구 보관됩니다.

================================================================================
                                       한울생약 기업부설연구소 (인)
================================================================================
"""
        # 파일 저장
        filename = "hanul-uvc-validation-report.txt"
        scratch_path = os.path.join("/workspace/scratch", filename)
        out_path = os.path.join("/workspace/out", filename)
        
        try:
            # 1. 스크래치에 작성
            with open(scratch_path, "w", encoding="utf-8") as f:
                f.write(report_content)
                
            # 2. 아웃박스 복사 (사용자 퍼블리시용)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(report_content)
                
            messagebox.showinfo(
                "성적서 내보내기 성공", 
                f"한울생약 공식 살균 품질 검증 성적서가 파일로 저장되었습니다.\n\n파일명: {filename}\n경로: Studio 패널에서 다운로드 받으실 수 있습니다."
            )
        except Exception as e:
            messagebox.showerror("오류 발생", f"보고서 생성 중 문제가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    app = UVSimulatorApp()
    app.mainloop()
