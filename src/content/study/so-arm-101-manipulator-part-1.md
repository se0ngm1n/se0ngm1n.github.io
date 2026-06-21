---
title: "SO-ARM 101 Manipulator Project Part 1"
date: 2026-06-21
category: "Manipulator Project"
summary: "SO-ARM 101 리더·팔로워 암의 조립, 모터 ID 설정, 캘리브레이션, 텔레오퍼레이션 검증 기록"
tags:
  - SO-ARM 101
  - LeKiwi
  - Teleoperation
  - Calibration
  - Imitation Learning
  - Behavior Cloning
  - AnySkin
thumbnail: "/study-media/so-arm-101-part-1/video-04-poster.jpg"
---

로봇암 프로젝트 시작, 중고나라에서 SO-ARM 101 + Lekiwi 키트를 합쳐서 42만원에 구입.

로봇암으로 파지 제어 프로젝트를 할 예정이라 곧 Anyskin 센서도 살 예정이다!

최종적으로 Lekiwi에 태워서 돌아다니게 하는게 목표이다.

<figure class="project-media project-media--video">
  <video controls muted playsinline preload="metadata" poster="/study-media/so-arm-101-part-1/video-01-poster.jpg">
    <source src="/study-media/so-arm-101-part-1/video-01.mp4" type="video/mp4" />
    브라우저에서 동영상을 재생할 수 없습니다.
  </video>
  <figcaption>구입한 SO-ARM 101과 LeKiwi 키트의 초기 상태 확인</figcaption>
</figure>

## 시스템 구성과 프로젝트 목표

SO-ARM 101은 사람이 직접 움직이는 **리더 암**과 그 관절 움직임을 따라가는 **팔로워 암**으로 구성했다. 먼저 두 암 사이의 텔레오퍼레이션을 안정적으로 구현하고, 이후 팔로워 암의 관절 상태와 카메라 영상을 함께 기록해 행동복제학습에 사용할 데이터셋을 구축할 계획이다.

단순히 고정된 작업대에서 물체를 집는 데서 끝내지 않고, 이동 플랫폼인 LeKiwi와 결합해 필요한 위치로 이동한 뒤 조작 작업을 수행하는 모바일 매니퓰레이터로 확장하는 것이 최종 목표다. 여기에 AnySkin 촉각 센서를 그리퍼에 추가하면 접촉 여부와 파지 상태를 시각 정보만으로 판단할 때보다 직접적으로 감지할 수 있다.

### 전체 제어 흐름

현재 단계에서는 리더 암이 사람의 시연을 입력받는 텔레오퍼레이터이고, 팔로워 암이 실제 동작을 수행하는 로봇이다. 이후 데이터 수집 단계에서는 이 제어 흐름에 카메라 관측과 촉각 관측을 추가한다.

```text
사람의 손
  -> 리더 암 관절 위치
  -> 캘리브레이션 및 안전 범위 적용
  -> 팔로워 암 목표 관절 위치
  -> 실제 로봇 동작

카메라 영상 + 팔로워 암 상태 + AnySkin 촉각값
  -> 시간 동기화
  -> LeRobotDataset episode
  -> 행동복제 정책 학습
```

LeRobot은 텔레오퍼레이션 입력, 데이터셋에 저장할 행동, 로봇에 전달할 명령을 각각의 처리 파이프라인으로 나눌 수 있다. 이 구조를 사용하면 관절 위치를 그대로 저장할지, end-effector pose나 상대 이동량으로 변환해 저장할지 명시적으로 선택할 수 있다. 자세한 구조는 [LeRobot의 Robot Processor 공식 문서](https://huggingface.co/docs/lerobot/processors_robots_teleop)에 정리되어 있다.

<div class="project-media-grid">
  <figure class="project-media">
    <img src="/study-media/so-arm-101-part-1/01-kit-listing.png" alt="중고로 구입한 SO-ARM 101과 LeKiwi 키트 판매 화면" loading="lazy" decoding="async" />
    <figcaption>SO-ARM 101과 LeKiwi 키트 구성 확인</figcaption>
  </figure>
  <figure class="project-media">
    <img src="/study-media/so-arm-101-part-1/02-kit-arrival.jpg" alt="조립 전 바닥에 펼쳐 둔 SO-ARM 101 부품과 공구" loading="lazy" decoding="async" />
    <figcaption>조립 전 부품과 서보모터 정리</figcaption>
  </figure>
</div>

## 모터 ID 설정

모터별로 아이디 부여

여러 개의 서보모터가 하나의 통신 라인에 연결되기 때문에 각 관절을 구분할 고유 ID가 필요하다. 조립 전에 모터 ID와 실제 관절 위치를 대응시켜 두어야 제어 명령이 의도한 관절에 전달되고, 이후 캘리브레이션 과정에서도 관절 순서를 혼동하지 않는다.

리더 암과 팔로워 암은 같은 관절 구조를 사용하므로 양쪽의 ID 체계를 일관되게 맞췄다. 이 단계에서 각 모터의 응답과 회전 방향도 함께 확인해 조립 이후 발생할 수 있는 배선 및 설정 문제를 줄였다.

SO-ARM101의 직렬 버스에서는 각 모터가 고유 ID로 구분되고, 컨트롤러와 모든 모터가 같은 baudrate를 사용해야 통신할 수 있다. 새 모터는 동일한 기본 ID를 가진 경우가 있기 때문에 처음에는 모터를 하나씩 연결해 ID와 baudrate를 기록한다. 이 설정은 모터의 비휘발성 메모리에 저장되므로 정상적으로 완료되면 매번 반복할 필요는 없다. 이 절차는 [SO-101 공식 설치 문서](https://huggingface.co/docs/lerobot/en/so101)의 모터 설정 단계와 동일한 흐름이다.

사용한 포트를 다시 확인하고 모터를 설정할 때 사용할 수 있는 명령은 다음과 같다. 실제 실행 시에는 포트 문자열을 현재 장치에 맞게 바꿔야 한다.

```bash
# USB를 분리하는 방식으로 리더/팔로워 포트 식별
lerobot-find-port

FOLLOWER_PORT=/dev/tty.usbmodemXXXX
LEADER_PORT=/dev/tty.usbmodemYYYY

# 팔로워 암 모터 ID와 baudrate 설정
lerobot-setup-motors \
  --robot.type=so101_follower \
  --robot.port="$FOLLOWER_PORT"

# 리더 암 모터 ID와 baudrate 설정
lerobot-setup-motors \
  --teleop.type=so101_leader \
  --teleop.port="$LEADER_PORT"
```

<figure class="project-media">
  <img src="/study-media/so-arm-101-part-1/03-assembly.jpg" alt="SO-ARM 101의 관절과 그리퍼를 조립하는 과정" loading="lazy" decoding="async" />
  <figcaption>관절 방향과 배선 간섭을 확인하며 로봇암 조립</figcaption>
</figure>

## 조립과 캘리브레이션

조립 시작, 천천히 유튜브 보면서 하니 아이디 부여하고 조립하고 캘리브레이션까지 4시간 정도 걸린 것 같다

조립 과정에서는 링크 방향과 서보모터의 초기 위치가 잘못 맞물리지 않도록 확인했다. 외형 조립만 끝내는 것이 아니라 관절을 전체 가동 범위에서 천천히 움직여 보면서 배선이 당겨지거나 구조물과 충돌하는 구간이 없는지도 점검했다.

<figure class="project-media project-media--video">
  <video controls muted playsinline preload="metadata" poster="/study-media/so-arm-101-part-1/video-02-poster.jpg">
    <source src="/study-media/so-arm-101-part-1/video-02.mp4" type="video/mp4" />
    브라우저에서 동영상을 재생할 수 없습니다.
  </video>
  <figcaption>리더 암의 관절 가동 범위를 기준으로 캘리브레이션 진행</figcaption>
</figure>

리더암 캘리브레이션 진행

리더 암의 각 관절을 최소·최대 범위로 움직이며 센서 값과 실제 자세의 대응 관계를 설정했다. 리더 암에서 읽은 관절 위치가 이후 팔로워 암의 목표값이 되므로, 작은 오프셋도 누적되면 두 암의 끝단 자세가 달라질 수 있다.

<figure class="project-media project-media--video">
  <video controls muted playsinline preload="metadata" poster="/study-media/so-arm-101-part-1/video-03-poster.jpg">
    <source src="/study-media/so-arm-101-part-1/video-03.mp4" type="video/mp4" />
    브라우저에서 동영상을 재생할 수 없습니다.
  </video>
  <figcaption>팔로워 암의 관절 범위와 기준 자세 캘리브레이션</figcaption>
</figure>

팔로우암 캘리브레이션 진행

팔로워 암도 동일하게 관절별 가동 범위와 기준 위치를 설정했다. 양쪽 암의 기구학적 기준을 맞춘 뒤에는 리더 암을 천천히 움직이며 팔로워 암이 같은 방향과 비슷한 크기로 움직이는지 관절별로 확인했다.

### 캘리브레이션이 필요한 이유

같은 자세를 취하더라도 리더 암과 팔로워 암에서 읽히는 모터 원시값은 조립 오프셋과 모터별 가동 범위 차이 때문에 정확히 같지 않을 수 있다. 캘리브레이션은 각 관절의 중앙 자세와 전체 가동 범위를 측정해 서로 다른 원시값을 동일한 관절 의미로 해석할 수 있게 만든다. [LeRobot SO-101 문서](https://huggingface.co/docs/lerobot/en/so101)는 리더와 팔로워를 같은 물리 자세로 놓았을 때 같은 위치값을 갖도록 맞추는 과정을 강조한다.

개념적으로 관절 `i`의 원시 위치 `r_i`를 0과 1 사이의 값으로 정규화하면 다음과 같이 표현할 수 있다.

\[
u_i = \operatorname{clip}\left(
\frac{r_i-r_{i,\min}}{r_{i,\max}-r_{i,\min}}, 0, 1
\right)
\]

이 값을 팔로워 암의 가동 범위로 다시 변환하면 리더와 팔로워의 물리적 범위 차이를 흡수할 수 있다.

\[
q_i^{F}=q_{i,\min}^{F}+u_i\left(q_{i,\max}^{F}-q_{i,\min}^{F}\right)
\]

위 식은 캘리브레이션의 목적을 설명하기 위한 개념식이다. 실제 변환과 저장 형식은 설치한 LeRobot 버전의 구현을 따른다.

```bash
lerobot-calibrate \
  --robot.type=so101_follower \
  --robot.port="$FOLLOWER_PORT" \
  --robot.id=so101_follower_main

lerobot-calibrate \
  --teleop.type=so101_leader \
  --teleop.port="$LEADER_PORT" \
  --teleop.id=so101_leader_main
```

여기서 지정한 `id`는 캘리브레이션 파일을 찾는 키로 사용되므로 이후 텔레오퍼레이션, 데이터 기록, 정책 평가에서도 같은 값을 사용해야 한다.

## 텔레오퍼레이션 검증

<figure class="project-media project-media--video">
  <video controls muted playsinline preload="metadata" poster="/study-media/so-arm-101-part-1/video-04-poster.jpg">
    <source src="/study-media/so-arm-101-part-1/video-04.mp4" type="video/mp4" />
    브라우저에서 동영상을 재생할 수 없습니다.
  </video>
  <figcaption>리더 암의 움직임을 팔로워 암이 실시간으로 재현한 결과</figcaption>
</figure>

텔레오퍼레이션 결과

리더 암을 직접 조작했을 때 팔로워 암이 관절 움직임과 그리퍼 동작을 따라가는 것을 확인했다. 이 텔레오퍼레이션 구성이 안정화되면 사람이 작업을 시연하는 동안 관절 상태, 행동 명령, 카메라 관측값을 같은 시간축으로 저장할 수 있다. 이 데이터는 행동복제 모델이 관측으로부터 다음 행동을 학습하는 기반이 된다.

LeRobot의 기본 텔레오퍼레이션 명령은 다음 형태로 실행할 수 있다. 캘리브레이션 단계에서 사용한 장치 `id`를 그대로 재사용한다.

```bash
lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port="$FOLLOWER_PORT" \
  --robot.id=so101_follower_main \
  --teleop.type=so101_leader \
  --teleop.port="$LEADER_PORT" \
  --teleop.id=so101_leader_main
```

## 행동복제학습 설계

행동복제학습은 사람이 수행한 시연에서 관측값과 행동의 대응 관계를 지도학습으로 학습한다. 시점 `t`에서 전면·손목 카메라 영상, 팔로워 암 관절 상태, 촉각값을 관측 `o_t`로 구성하고, 같은 시점의 리더 암 명령을 목표 행동 `a_t`로 저장하는 방식이다.

\[
o_t = \left\{I_t^{front}, I_t^{wrist}, q_t, s_t^{skin}\right\},
\qquad
D = \left\{(o_t, a_t)\right\}_{t=1}^{N}
\]

- `I_t`: 카메라 이미지
- `q_t`: 팔로워 암의 관절 상태
- `s_t^{skin}`: AnySkin 촉각 센서 특징
- `a_t`: 리더 암으로 만든 목표 관절 행동

연속 관절 행동을 직접 회귀하는 가장 단순한 행동복제 손실은 평균제곱오차로 표현할 수 있다.

\[
\mathcal{L}_{BC}(\theta)=
\frac{1}{N}\sum_{t=1}^{N}
\left\|\pi_{\theta}(o_t)-a_t\right\|_2^2
\]

단일 시점 행동만 예측하면 작은 오차가 시간에 따라 누적될 수 있다. 초기 학습 모델로 고려하는 ACT(Action Chunking with Transformers)는 한 시점의 행동 대신 여러 미래 행동으로 구성된 chunk를 예측한다.

\[
A_t=\left[a_t,a_{t+1},\ldots,a_{t+K-1}\right]
\]

[ACT 원 논문](https://arxiv.org/abs/2304.13705)은 행동 오차의 누적과 사람 시연의 비정상성을 다루기 위해 action chunking을 제안한다. [LeRobot ACT 공식 문서](https://huggingface.co/docs/lerobot/act)에서도 ACT를 저비용 로봇의 정밀 조작을 위한 기본 행동복제 정책으로 안내하고 있다.

### 데이터 수집 명령 초안

아래 명령은 카메라 연결 후 사용할 기록 설정의 초안이다. 카메라 index와 해상도는 실제 장치에서 `lerobot-find-cameras`로 확인한 뒤 수정한다.

```bash
HF_USER=your_huggingface_id

lerobot-record \
  --robot.type=so101_follower \
  --robot.port="$FOLLOWER_PORT" \
  --robot.id=so101_follower_main \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 1, width: 640, height: 480, fps: 30} }" \
  --teleop.type=so101_leader \
  --teleop.port="$LEADER_PORT" \
  --teleop.id=so101_leader_main \
  --dataset.repo_id="${HF_USER}/so101_fragile_pick_place" \
  --dataset.num_episodes=50 \
  --dataset.single_task="pick up the fragile object and place it in the tray" \
  --dataset.streaming_encoding=true \
  --display_data=true
```

[LeRobot 실물 로봇 가이드](https://huggingface.co/docs/lerobot/main/en/getting_started_real_world_robot)는 초기 데이터 수집에서 카메라를 고정하고 일관된 파지 방식을 유지한 뒤, 성능이 확보되면 물체 위치와 파지 방법의 변화를 점진적으로 늘리도록 권장한다. 이 프로젝트도 먼저 단일 물체와 제한된 위치에서 성공 궤적을 안정적으로 확보한 뒤 난이도를 높일 계획이다.

### ACT 학습 명령 초안

```bash
lerobot-train \
  --dataset.repo_id="${HF_USER}/so101_fragile_pick_place" \
  --policy.type=act \
  --output_dir=outputs/train/act_so101_fragile \
  --job_name=act_so101_fragile \
  --policy.device=cuda \
  --wandb.enable=true
```

## AnySkin 기반 적응형 파지 설계

카메라와 관절 상태만 사용하면 그리퍼가 물체 표면에 실제로 닿았는지, 파지 중 물체가 미끄러지는지를 직접 관측하기 어렵다. [AnySkin 논문](https://arxiv.org/abs/2409.08276)은 교체 가능한 자기식 촉각 센서 구조와 함께 slip detection 및 촉각 기반 policy learning 가능성을 검증했다. 이 프로젝트에서는 AnySkin 신호를 행동복제 정책의 추가 관측값으로 넣고, 별도의 안전 계층에서도 사용할 계획이다.

촉각 센서의 무접촉 기준값을 `s_0`, 현재 측정값을 `s_t`라고 하면 간단한 접촉 특징은 다음과 같이 만들 수 있다.

\[
\Delta s_t=s_t-s_0,
\qquad
c_t=\left\|\Delta s_t\right\|_2
\]

또한 짧은 시간 동안 촉각 패턴이 빠르게 변하는지를 이용해 미끄러짐 후보 특징을 구성할 수 있다.

\[
d_t=\left\|\Delta s_t-\Delta s_{t-1}\right\|_2
\]

다음 코드는 향후 실험할 안전 계층의 개념 예시다. 실제 물체에 적용하기 전에 낮은 속도와 보수적인 임계값으로 검증해야 한다.

```python
import numpy as np

delta = tactile - tactile_baseline
contact_level = np.linalg.norm(delta)
slip_level = np.linalg.norm(delta - previous_delta)

if contact_level > max_contact_level:
    gripper_target -= release_step
elif slip_level > slip_threshold:
    gripper_target += close_step

gripper_target = np.clip(gripper_target, gripper_min, gripper_max)
```

행동복제 정책이 제안한 그리퍼 명령을 그대로 실행하지 않고 촉각 기반 제한을 마지막에 적용하면, 학습 데이터에서 보지 못한 접촉 상황에서도 과도한 파지를 완화할 수 있다. 단, `contact_level`과 `slip_level`은 곧바로 힘의 절대값을 의미하지 않으므로 물체 종류별 실험을 통해 임계값을 정해야 한다.

## 다음 단계

다음 진행할거 -> 행동복제학습 데이터 수집하고 픽앤플레이스 구현

다음 단계에서는 물체의 초기 위치와 조명, 접근 방향을 바꾸어 여러 차례 시연 데이터를 수집할 예정이다. 먼저 고정된 작업대에서 단일 물체를 집어 지정 위치로 옮기는 Pick & Place를 구현하고, 성공률과 실패 원인을 기록해 데이터 품질과 정책의 일반화 성능을 개선한다.

이후 진행 계획은 다음과 같다.

1. 카메라 영상과 리더·팔로워 암의 관절 상태를 동기화해 시연 데이터 수집
2. 행동복제 정책을 학습하고 고정 환경에서 Pick & Place 성공률 평가
3. AnySkin 센서를 그리퍼에 장착해 접촉 및 미끄러짐 정보를 관측값에 추가
4. LeKiwi 이동 플랫폼과 통합해 이동 후 물체를 탐색하고 파지하는 전체 작업 구현

## 참고 자료

- [Hugging Face LeRobot: SO-101](https://huggingface.co/docs/lerobot/en/so101)
- [Hugging Face LeRobot: Getting Started with Real-World Robots](https://huggingface.co/docs/lerobot/main/en/getting_started_real_world_robot)
- [Hugging Face LeRobot: Processors for Robots and Teleoperators](https://huggingface.co/docs/lerobot/processors_robots_teleop)
- [Hugging Face LeRobot: ACT](https://huggingface.co/docs/lerobot/act)
- [Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware](https://arxiv.org/abs/2304.13705)
- [AnySkin: Plug-and-play Skin Sensing for Robotic Touch](https://arxiv.org/abs/2409.08276)
