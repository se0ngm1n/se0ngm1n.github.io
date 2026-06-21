---
title: "토크-열 피드백 보상 설계를 통한 강화학습 기반 사족보행 안정성 향상"
date: 2026-06-21
category: "Quadruped Project"
summary: "Unitree Go2/MuJoCo 사족보행 실험에서 Baseline, Thermal Feedback, Thermal-Torque Feedback를 비교하고 열 안정성과 직진성을 함께 정리한 종합설계 보고서 요약"
tags:
  - Unitree Go2
  - Reinforcement Learning
  - Reward Design
  - Thermal Feedback
  - Quadruped
  - MuJoCo
thumbnail: "/study-media/unitree-go2-thermal-torque-feedback/07-field-photo-2.png"
---

## 초록

본 연구는 강화학습 기반 사족보행에서 온도 피드백 보상 설계가 보행 안정성에 미치는 영향을 분석하고, 토크 부하를 함께 고려한 토크-열 피드백 보상 구조를 제안한다. Baseline, Thermal Feedback, Thermal-Torque Feedback 정책을 Unitree Go2/MuJoCo 환경의 1.5 m/s 조건에서 비교하였다. 단순 온도 피드백 정책은 평균 속도는 증가하였으나 10 m 직진 시 lateral drift와 yaw drift가 크게 증가하여 방향 안정성이 저하되었다. 반면 토크-열 피드백 정책은 final lateral drift 0.065 m, final yaw drift 0.49 deg로 가장 안정적인 직진 보행을 보였다. 이를 통해 사족보행의 열적 안정성 개선에는 온도 상태뿐 아니라 발열 원인인 토크/부하를 함께 반영한 보상 설계가 필요함을 확인하였다.

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/01-title-compare.png" alt="Baseline, Thermal Feedback, Thermal-Torque Feedback의 보행 궤적 비교" loading="lazy" decoding="async" />
  <figcaption>같은 속도 명령에서 세 정책의 보행 궤적을 비교한 요약 화면</figcaption>
</figure>

<figure class="project-media project-media--video">
  <video controls muted playsinline preload="metadata" poster="/study-media/unitree-go2-thermal-torque-feedback/05-gait-compare.png">
    <source src="/study-media/unitree-go2-thermal-torque-feedback/videos/01-ppt-video.mp4" type="video/mp4" />
    브라우저에서 동영상을 재생할 수 없습니다.
  </video>
  <figcaption>PPT 원본 보행 비교 영상</figcaption>
</figure>

## 1. 서론

사족보행 로봇은 다양한 지형에서 이동성이 높아 점검, 운송, 탐사 분야에 활용 가능성이 크다. 최근에는 강화학습을 이용해 복잡한 보행 정책을 학습하는 연구가 활발하며, 명령 속도 추종, 자세 안정성, 보행 리듬 등을 보상함수로 설계해 안정적인 locomotion policy를 얻는 방식이 널리 사용된다. 그러나 고속 또는 장시간 보행 상황에서는 특정 관절 구동기에 토크 부하가 집중될 수 있고, 이는 모터 손실과 온도 상승으로 이어져 보행 성능과 안정성에 영향을 준다.

열 문제를 고려하는 직관적인 방법은 motor temperature를 관측값 또는 보상함수에 포함하는 것이다. 하지만 온도는 토크 부하와 모터 손실이 누적된 결과값이므로, 단순히 온도 상태만 반영한 정책은 발열 원인을 직접 제어하지 못할 수 있다. 특히 제한된 observation history를 사용하는 정책에서는 장기적으로 누적되는 thermal state나 좌우 부하 불균형이 충분히 드러나지 않아 비대칭 보행이 학습될 가능성이 있다.

본 보고서는 이러한 문제를 확인하기 위해 Baseline, Thermal Feedback, Thermal-Torque Feedback의 세 정책을 비교한다. Baseline은 기본 보행 성능을 기준으로 하는 정책이고, Thermal Feedback은 온도 상태를 반영한 정책이다. Thermal-Torque Feedback은 온도뿐만 아니라 발열의 주요 원인인 토크/부하를 함께 고려하도록 설계하였다. Unitree Go2/MuJoCo 환경에서 1.5 m/s 조건의 보행 실험을 수행하고, lateral drift, yaw drift, energy per meter, motor temperature rise를 비교하여 토크-열 피드백 보상 설계가 보행 안정성에 미치는 영향을 분석하였다.

## 2. 강화학습 기반 보행 정책 및 보상 설계

강화학습 기반 사족보행 정책은 로봇의 현재 상태를 관측값으로 입력받아 각 관절에 대한 action을 출력하고, 이에 따른 보상의 누적값을 최대화하도록 학습된다. 본 연구에서 사용한 observation은 명령 속도, body/IMU 상태, 관절 위치와 속도, 이전 action 등으로 구성된다. 기본 보상함수는 명령 속도 추종, 자세 안정성, 자연스러운 보행 리듬, 낮은 effort, smooth action 등을 포함하여 기본적인 locomotion 성능을 유도한다.

그러나 이러한 기본 보상만으로는 장시간 또는 고속 보행 중 특정 관절에 발생하는 지속적인 토크 부하와 온도 상승을 직접적으로 제어하기 어렵다. 따라서 본 연구에서는 기본 보행 정책을 기준선으로 두고, 온도 상태를 반영한 정책과 토크 부하까지 함께 반영한 정책을 비교하였다.

### 비교 정책 구성

본 연구에서는 Baseline, Thermal Feedback, Thermal-Torque Feedback의 세 정책을 비교하였다. Baseline 정책은 속도 추종과 자세 안정성을 중심으로 학습되며 motor temperature를 직접 관측하지 않는다. Thermal Feedback 정책은 motor temperature, thermal margin, hotspot 정보를 추가로 사용하여 온도 상승을 억제하도록 설계하였다. Thermal-Torque Feedback 정책은 온도 상태뿐 아니라 발열의 원인이 되는 torque/load 부담을 함께 고려하여 고온 actuator에 큰 토크가 집중되는 현상을 억제하도록 설계하였다.

중요한 차이는 Thermal Feedback이 온도라는 결과값에 반응하는 정책인 반면, Thermal-Torque Feedback은 온도를 발생시키는 원인까지 보상함수에 포함한다는 점이다. 이 차이를 통해 단순한 온도 피드백과 물리적 원인을 고려한 보상 설계가 보행 안정성에 미치는 영향을 비교할 수 있다.

<table>
  <thead>
    <tr>
      <th>Policy</th>
      <th>Main feedback</th>
      <th>Role</th>
      <th>Expected limitation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Baseline</td>
      <td>Locomotion state</td>
      <td>기본 보행 기준선</td>
      <td>열 상태를 직접 고려하지 않음</td>
    </tr>
    <tr>
      <td>Thermal Feedback</td>
      <td>Temperature state</td>
      <td>온도 상승 억제</td>
      <td>온도는 결과값이므로 부하 원인을 직접 제어하기 어려움</td>
    </tr>
    <tr>
      <td>Thermal-Torque Feedback</td>
      <td>Temperature + torque/load</td>
      <td>발열 원인과 결과를 함께 제어</td>
      <td>보상 가중치 설계가 필요함</td>
    </tr>
  </tbody>
</table>

### 보상 설계

세 정책은 공통적으로 속도 추종, 자세 유지, 발 움직임, 종료 패널티와 같은 기본 locomotion reward를 사용한다. Thermal Feedback 정책은 여기에 actuator 온도 변화량을 억제하는 thermal reward를 추가한다. Thermal-Torque Feedback 정책은 추가로 고온 actuator에 큰 torque가 집중되는 것을 억제하는 항과, 온도가 높을수록 torque 사용 여유를 줄이는 항을 포함한다.

전체 보상은 다음과 같은 형태로 정리할 수 있다.

<div class="formula-block formula-block--stacked" role="math" aria-label="total reward composed of locomotion thermal and torque terms">
  <span><var>r</var><sub>total</sub> = <var>r</var><sub>locomotion</sub> + <var>λ</var><sub>T</sub><var>r</var><sub>thermal</sub> + <var>λ</var><sub>τ</sub><var>r</var><sub>torque</sub></span>
</div>

여기서 `r_locomotion`은 기본 보행 성능 보상, `r_thermal`은 온도 상승 억제 보상, `r_torque`는 과도한 토크 또는 부하 집중에 대한 패널티이다. Baseline은 `r_locomotion`만 사용하고, Thermal Feedback은 `r_thermal`을 추가하며, Thermal-Torque Feedback은 `r_thermal`과 `r_torque`를 함께 사용한다.

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/04-reward-hacking.png" alt="보상 해킹의 예시를 보여주는 도식" loading="lazy" decoding="async" />
  <figcaption>온도만 단독 보상으로 둘 때 발생할 수 있는 reward hacking 예시</figcaption>
</figure>

## 3. 데이터 수집 및 열-부하 해석 모델

### 실로봇 데이터 수집 및 전처리

본 연구에서는 강화학습 정책의 열적 특성을 해석하기 위해 Unitree Go2의 sim-to-real 보행 과정에서 수집한 low-level 데이터를 사용하였다. 로봇의 상태와 명령은 ROS bag 형태로 저장하였으며, 주요 topic은 `/lowstate`와 `/lowcmd`이다. 원본 raw rosbag directory는 총 30개였고, 이 중 분석에 사용할 수 있도록 policy joint order에 맞추어 변환한 low-state CSV는 24개이다.

각 데이터는 약 10분에서 50분 동안 수집되었으며, 분석에는 실제 보행이 이루어진 active walking 구간을 중심으로 10분 window를 사용하였다. 최종적으로 20개의 train window와 4개의 test window를 구성하였고, 속도 조건은 0.5-1.5 m/s 범위의 실험 metadata를 기준으로 정리하였다. 이러한 전처리는 실제 모터 순서와 강화학습 policy에서 사용하는 joint order를 일치시키고, 토크, 각속도, 온도, 배터리 상태를 동일한 시간축에서 비교하기 위해 수행하였다.

사용한 데이터 항목은 총 52개로 구성된다. 12개 모터에 대해 관절 위치 `q`, 관절 속도 `dq`, 추정 토크 `tau_est`, motor temperature를 사용하여 48개 motor telemetry를 구성하였다. 여기에 battery voltage, battery current, BMS SOC 관련 항목을 추가하여 전체 구동 전력과 배터리 상태를 함께 해석할 수 있도록 하였다.

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/02-field-photo-1.png" alt="실외 바닥에서 측정 중인 Unitree Go2와 노트북 화면" loading="lazy" decoding="async" />
  <figcaption>실로봇 보행 데이터 수집 장면</figcaption>
</figure>

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/07-field-photo-2.png" alt="실외 바닥 위에 놓인 Unitree Go2와 연결 케이블" loading="lazy" decoding="async" />
  <figcaption>실험 환경과 로봇 연결 상태 확인</figcaption>
</figure>

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/08-rosbag-preprocess.png" alt="rosbag 데이터를 lowstate CSV로 정리하는 전처리 개요" loading="lazy" decoding="async" />
  <figcaption>rosbag 데이터를 학습 가능한 형식으로 정리하는 전처리 흐름</figcaption>
</figure>

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/06-dataflow.png" alt="관측값과 행동, 정책 학습으로 이어지는 데이터 흐름" loading="lazy" decoding="async" />
  <figcaption>관측값, 행동, 학습 데이터셋으로 이어지는 전체 흐름</figcaption>
</figure>

### 열-부하 해석 모델

시뮬레이션에서 직접 얻을 수 있는 값은 각 관절의 토크와 각속도이다. 그러나 보행 중 발생하는 열 부담과 배터리 에너지 사용량을 해석하기 위해서는 토크, 각속도, 모터 발열, 모터 온도, 배터리 부하 사이의 관계를 모델링할 필요가 있다. 본 연구에서는 기존 물리 모델을 기반으로 한 grey-box 열-부하 모델을 사용하였다.

모터의 열 입력은 토크 제곱 기반의 구리손실, 속도 기반 마찰손실, Coulomb-type 손실, 그리고 모터 그룹별 bias 발열을 합산하여 다음과 같이 나타낼 수 있다.

### Torque → Heat

<div class="formula-block formula-block--stacked" role="math" aria-label="motor heat input equation">
  <span><var>P</var><sub>heat,i</sub> = <var>k</var><sub>τ,25</sub>[1 + <var>α</var><sub>Cu</sub>(<var>T</var><sub>i</sub> - <var>T</var><sub>ref</sub>)]<var>τ</var><sub>i</sub><sup>2</sup> + <var>b</var><sub>v</sub><var>ω</var><sub>i</sub><sup>2</sup> + <var>τ</var><sub>c</sub>|<var>ω</var><sub>i</sub>| + <var>P</var><sub>bias,g(i)</sub></span>
</div>

여기서 `tau_i`와 `omega_i`는 각각 i번째 관절의 토크와 각속도이며, `T_i`는 해당 모터 온도이다. `g(i)`는 i번째 모터가 속한 motor group을 의미하며, 본 연구에서는 Hip, Thigh, Calf 그룹으로 나누어 열 특성을 fitting하였다.

### Heat → Motor Heat

<div class="formula-block formula-block--stacked" role="math" aria-label="motor temperature transition equation">
  <span><var>T</var><sub>i</sub>(t + Δt) = <var>T</var><sub>amb</sub> + e<sup>-Δt / <var>τ</var><sub>th,g(i)</sub></sup>[<var>T</var><sub>i</sub>(t) - <var>T</var><sub>amb</sub>] + <var>R</var><sub>th,g(i)</sub>(1 - e<sup>-Δt / <var>τ</var><sub>th,g(i)</sub></sup>)<var>P</var><sub>heat,i</sub></span>
</div>

<div class="formula-block formula-block--stacked" role="math" aria-label="load power equation">
  <span><var>P</var><sub>load</sub> = <var>P</var><sub>base</sub> + Σ<sub>i</sub>[max(<var>τ</var><sub>i</sub><var>ω</var><sub>i</sub>, 0) / <var>η</var><sub>drive</sub> + <var>k</var><sub>τ,25</sub><var>τ</var><sub>i</sub><sup>2</sup> + <var>b</var><sub>v</sub><var>ω</var><sub>i</sub><sup>2</sup> + <var>τ</var><sub>c</sub>|<var>ω</var><sub>i</sub>|]</span>
</div>

이 모델의 목적은 모터 내부 권선 온도를 정밀하게 예측하는 것보다, 정책 평가에서 torque/load가 motor temperature rise와 energy consumption으로 연결되는 경로를 해석하는 데 있다. 따라서 본 연구에서는 해당 모델을 통해 단순한 온도 피드백보다 토크/부하를 함께 고려한 보상 설계가 필요한 이유를 물리적으로 설명하였다.

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/09-thermal-model.png" alt="토크, 열입력, 온도 예측을 연결한 수식 정리" loading="lazy" decoding="async" />
  <figcaption>토크에서 열 입력, 그리고 온도 예측으로 이어지는 모델 정리</figcaption>
</figure>

## 4. 실험 조건 및 평가 지표

### 실험 조건

본 연구에서는 세 가지 강화학습 정책의 보행 안정성과 열적 부담을 비교하기 위해 Unitree Go2 모델을 사용한 MuJoCo 기반 시뮬레이션 평가를 수행하였다. 비교 대상은 Baseline, Thermal Feedback, Thermal-Torque Feedback 정책이며, 모든 정책은 동일한 명령 속도 조건에서 평가하였다. 주요 명령 속도는 `vx = 1.5 m/s`로 설정하였으며, 고속 보행 상황에서 torque/load 분포와 방향 안정성이 어떻게 달라지는지 확인하였다.

정책 평가는 크게 두 가지 실험으로 구성하였다. 첫째, 20분 보행 실험을 통해 장시간 보행 중 이동거리, 평균 속도, 최대 모터 온도, 이동 거리당 에너지 사용량을 비교하였다. 둘째, 10 m 직진 명령 실험을 통해 lateral drift와 yaw drift를 측정하여 직진 안정성을 평가하였다. 또한 후속 분석에서는 480 s MuJoCo 평가를 통해 국소 열위험을 나타내는 thermal-risk 보조 지표를 별도로 확인하였다.

### 보행 성능 및 에너지 지표

20분 보행 실험에서는 각 정책이 동일한 속도 명령에서 얼마나 안정적으로 장시간 보행을 유지하는지 확인하였다. 평가 지표로는 이동거리, 평균 속도, 최대 모터 온도, energy per meter를 사용하였다. 이동거리와 평균 속도는 명령 속도 추종 성능을 나타내며, 최대 모터 온도는 보행 중 가장 높은 열 부담을 받은 actuator의 상태를 나타낸다. Energy per meter는 단위 이동거리당 필요한 구동 부담을 의미하므로, 보행 효율을 비교하는 지표로 사용하였다.

### 직진 안정성 지표

10 m 직진 명령 실험에서는 정책이 목표 방향을 얼마나 잘 유지하는지 평가하였다. 이를 위해 10 m 도달 시점의 lateral drift와 yaw drift, 종료 시점의 final lateral abs와 final yaw abs를 사용하였다. Lateral drift는 로봇이 목표 직선 경로에서 좌우로 벗어난 정도를 나타내며, yaw drift는 heading 방향이 얼마나 틀어졌는지를 나타낸다.

특히 본 연구의 핵심 관심사는 thermal feedback이 보행 안정성을 해치지 않으면서 열 부담을 줄일 수 있는지 여부이다. 따라서 Thermal Feedback 정책이 높은 속도를 달성하더라도 lateral drift나 yaw drift가 증가한다면, 이는 안정적인 보행 개선으로 보기 어렵다. 반대로 Thermal-Torque Feedback 정책이 온도와 torque/load를 함께 고려하여 drift를 줄인다면, 이는 보상 설계가 locomotion stability와 더 잘 정렬되었음을 의미한다.

<div class="project-media-grid">
  <figure class="project-media">
    <img src="/study-media/unitree-go2-thermal-torque-feedback/10-energy-compare.png" alt="세 정책의 에너지 사용량과 모터 온도 비교 그래프" loading="lazy" decoding="async" />
    <figcaption>20분 보행 후 에너지와 온도 지표 비교</figcaption>
  </figure>
  <figure class="project-media">
    <img src="/study-media/unitree-go2-thermal-torque-feedback/11-straightness-compare.png" alt="세 정책의 직진성 비교 그래프" loading="lazy" decoding="async" />
    <figcaption>10 m 직진 명령에서의 방향 안정성 비교</figcaption>
  </figure>
</div>

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/13-result-yaw.png" alt="세 정책의 보행 궤적과 yaw drift를 보여주는 비교 화면" loading="lazy" decoding="async" />
  <figcaption>같은 속도 명령에서 세 정책의 보행 궤적과 yaw drift를 비교한 화면</figcaption>
</figure>

<figure class="project-media">
  <img src="/study-media/unitree-go2-thermal-torque-feedback/14-reason-analysis.png" alt="Thermal 정책의 성능이 낮은 이유를 설명하는 분석 화면" loading="lazy" decoding="async" />
  <figcaption>Thermal 정책이 단독 온도 보상만으로는 불안정해지는 이유</figcaption>
</figure>

<figure class="project-media project-media--video">
  <video controls muted playsinline preload="metadata" poster="/study-media/unitree-go2-thermal-torque-feedback/11-straightness-compare.png">
    <source src="/study-media/unitree-go2-thermal-torque-feedback/videos/02-ppt-video.mp4" type="video/mp4" />
    브라우저에서 동영상을 재생할 수 없습니다.
  </video>
  <figcaption>PPT 원본 직진성 비교 영상</figcaption>
</figure>

## 5. 결과 및 해석

### 20분 보행 결과

Baseline 정책은 1542 m를 이동하였고, 평균 속도는 1.285 m/s, 최대 모터 온도는 71 deg C, energy per meter는 48 W/m로 나타났다. Thermal Feedback 정책은 1656 m로 가장 긴 이동거리와 1.379 m/s의 평균 속도를 보였으나, 최대 모터 온도는 95 deg C, energy per meter는 63 W/m로 증가하였다. 반면 Thermal-Torque Feedback 정책은 1612 m를 이동하여 Baseline보다 긴 이동거리를 보였고, 평균 속도도 1.343 m/s로 향상되었다. 동시에 최대 모터 온도는 67 deg C, energy per meter는 45 W/m로 세 정책 중 가장 낮게 나타났다.

정량 결과는 열 피드백이 속도를 끌어올릴 수는 있어도, 그것이 곧 좋은 보행 성능을 뜻하지는 않는다는 점을 보여준다. Thermal Feedback 정책은 가장 빠르게 이동했지만 열 부담과 에너지 사용량이 크게 증가하였다. 이는 온도 상태만을 보상에 포함하는 방식이 actuator load를 균형 있게 분산시키지 못할 수 있음을 의미한다.

### 10 m 직진성 결과

10 m 직진성 실험에서는 Baseline 정책이 lateral drift +0.502 m, yaw drift +2.73 deg를 보였고, final lateral abs와 final yaw abs는 각각 0.515 m, 2.92 deg였다. Thermal Feedback 정책은 lateral drift -1.255 m, yaw drift -18.22 deg로 방향 안정성이 크게 저하되었으며, final lateral abs와 final yaw abs도 각각 1.311 m, 18.21 deg로 증가하였다. 반면 Thermal-Torque Feedback 정책은 lateral drift -0.065 m, yaw drift -0.34 deg를 보였고, final lateral abs와 final yaw abs는 각각 0.065 m, 0.49 deg로 가장 작았다.

위 결과는 본 연구의 핵심 결론을 잘 보여준다. Thermal Feedback은 온도 상태를 반영했음에도 불구하고 보행 방향이 크게 틀어졌으며, 에너지 사용량과 온도 상승도 증가하였다. 반면 Thermal-Torque Feedback은 온도와 함께 torque/load 부담을 보상함수에 반영함으로써 가장 작은 drift를 보였다. 따라서 열적 안정성을 고려한 보행 정책에서는 온도라는 결과값뿐 아니라 발열의 원인인 torque/load를 함께 제어해야 함을 확인할 수 있다.

<div class="project-media-grid">
  <figure class="project-media">
    <img src="/study-media/unitree-go2-thermal-torque-feedback/15-final-table.jpeg" alt="최종 결과표" loading="lazy" decoding="async" />
    <figcaption>최종 수치 비교표</figcaption>
  </figure>
  <figure class="project-media">
    <img src="/study-media/unitree-go2-thermal-torque-feedback/16-final-summary.png" alt="최종 결론을 요약한 화면" loading="lazy" decoding="async" />
    <figcaption>실험 결과를 한 장으로 정리한 결론 화면</figcaption>
  </figure>
</div>

<figure class="project-media project-media--video">
  <video controls muted playsinline preload="metadata" poster="/study-media/unitree-go2-thermal-torque-feedback/16-final-summary.png">
    <source src="/study-media/unitree-go2-thermal-torque-feedback/videos/03-ppt-video.mp4" type="video/mp4" />
    브라우저에서 동영상을 재생할 수 없습니다.
  </video>
  <figcaption>PPT 원본 최종 요약 영상</figcaption>
</figure>

### 국소 열위험 보조 지표

후속 480 s MuJoCo thermal-risk 평가에서는 Thermal-Torque Feedback이 Baseline 대비 corrected thermal dose per meter, peak reported-temperature rise per meter, hotspot dose per meter를 각각 22.5%, 13.2%, 27.0% 감소시켰다. 이 결과는 10 m 직진성 결과와는 별도의 보조 evidence로, torque/load를 보상에 포함한 정책이 국소적인 열 집중을 줄이는 데에도 기여할 수 있음을 보여준다.

다만 이 지표는 20분 보행 실험 및 10 m 직진성 실험과 평가 길이 및 metric 정의가 다르다. 따라서 본 연구에서는 해당 결과를 주 결과와 직접 평균내지 않고, Thermal-Torque Feedback의 물리적 해석을 보강하는 보조 결과로 사용하였다.

강화학습 기반 locomotion policy는 MDP 위에서 누적 reward를 최대화하도록 학습된다. 그러나 본 연구에서 사용한 policy는 LSTM과 같이 장기 내부 memory를 유지하는 구조가 아니며, control step마다 현재 observation과 제한된 history만으로 action을 결정한다. 이 경우 장기적으로 누적되는 actuator temperature, 특정 motor의 지속적인 부하 집중, 좌우 열 분포 불균형은 짧은 observation window에 충분히 드러나지 않을 수 있다.

Temperature-aware reward만 추가하면 정책은 전체 actuator의 열 부하를 균형 있게 낮추는 전략이 아니라, reward function의 빈틈을 이용해 특정 leg 또는 actuator에 torque demand를 집중시키는 전략을 학습할 수 있다. 이 경우 asymmetric torque allocation이 발생하고, gait symmetry가 무너지며, yaw drift와 lateral drift가 증가한다. 본 연구에서 Thermal Feedback 정책이 빠르지만 방향 안정성이 악화된 것은 이러한 failure mode와 일치한다.

Torque-aware regularization은 이러한 문제를 줄이는 physical regularizer로 작용한다. 과도한 torque 또는 current demand는 motor heating의 직접 원인이므로, torque/load margin을 penalty로 제한하면 temperature reward만으로 억제되지 않던 비정상적인 부하 집중을 줄일 수 있다. 결과적으로 Thermal-Torque Feedback은 온도 결과와 발열 원인을 함께 제어하여 yaw 방향 틀어짐을 줄이고, 직진 안정성을 유지하면서 열 부담을 낮추는 방향으로 학습되었다.

## 6. 결론

본 연구에서는 강화학습 기반 사족보행에서 온도 피드백 보상 설계가 보행 안정성에 미치는 영향을 분석하고, 발열 원인인 토크/부하를 함께 고려한 토크-열 피드백 보상 구조를 제안하였다. 이를 위해 Baseline, Thermal Feedback, Thermal-Torque Feedback의 세 정책을 Unitree Go2/MuJoCo 환경에서 비교하였다.

실험 결과, 단순히 motor temperature를 반영한 Thermal Feedback 정책은 평균 속도는 증가하였으나 lateral drift, yaw drift, energy per meter, Tmax rise가 모두 증가하여 안정적인 보행 개선으로 이어지지 않았다. 이는 온도가 발열의 결과값이며, 제한된 observation history만으로는 장기적인 thermal state와 비대칭 torque allocation을 충분히 제어하기 어렵기 때문으로 해석된다.

반면 Thermal-Torque Feedback 정책은 온도 상태와 함께 torque/load 부담을 보상함수에 반영함으로써 10 m 직진 실험에서 final lateral drift 0.065 m, final yaw drift 0.49 deg로 가장 작은 방향 오차를 보였다. 또한 20분 보행 실험에서도 Thermal Feedback 대비 에너지 사용량과 최대 모터 온도를 낮추어, 보행 안정성과 열 부담 사이의 균형을 개선하였다. 따라서 사족보행 로봇의 thermal-aware locomotion을 위해서는 온도 상태를 단순히 추가하는 것보다, 발열을 유발하는 물리적 원인을 보상 설계에 함께 반영하는 것이 중요하다.

향후 연구에서는 동일한 초기 온도, 배터리 상태, 지면 조건, command sequence를 통제한 실로봇 장시간 반복 실험이 필요하다. 또한 장기 thermal state를 더 잘 반영하기 위해 recurrent policy 또는 thermal state estimator를 결합하는 방법을 검토할 수 있다.

## 후기

본 연구는 2026학년도 종합설계 교과목의 일환으로 수행되었으며, 연구 진행 과정에서 지도와 조언을 주신 김남수 교수님께 감사드립니다.

## 참고문헌

1. Wensing, P. M., Wang, A., Seok, S., Otten, D., Lang, J. and Kim, S., 2017, "Proprioceptive Actuator Design in the MIT Cheetah: Impact Mitigation and High-Bandwidth Physical Interaction for Dynamic Legged Robots," IEEE Transactions on Robotics, Vol. 33, No. 3, pp. 509-522.
2. Wallscheid, O. and Bcker, J., 2016, "Global Identification of a Low-Order Lumped-Parameter Thermal Network for Permanent Magnet Synchronous Motors," IEEE Transactions on Energy Conversion, Vol. 31, No. 1, pp. 354-365.
3. Lin, W., Qian, L., Luo, X. and Liang, C., 2025, "Temperature Distribution Prediction of the Quadruped Robot Based on the Lumped-Parameter Thermal Networks," Robot, Vol. 47, No. 2, pp. 188-199.
4. Wang, Q., Gao, T. and Li, X., 2022, "SOC Estimation of Lithium-Ion Battery Based on Equivalent Circuit Model with Variable Parameters," Energies, Vol. 15, No. 16, 5829.
5. Bernardi, D., Pawlikowski, E. and Newman, J., 1985, "A General Energy-Balance for Battery Systems," Journal of the Electrochemical Society, Vol. 132, No. 1, pp. 5-12.
