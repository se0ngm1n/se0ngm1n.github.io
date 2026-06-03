---
title: "[IsaacLab Part 5] Mimic과 Robomimic으로 Franka Cube Stacking BC 학습하기"
date: 2026-06-02
category: "Isaac Lab"
summary: "NVIDIA Isaac Lab 공식 Franka cube stacking demonstration dataset으로 Mimic subtask annotation, 추가 demonstration 생성, Robomimic Behavior Cloning 학습과 checkpoint 생성을 실행한 과정을 정리한다."
tags:
  - Isaac Sim
  - Isaac Lab
  - Imitation Learning
  - Behavior Cloning
  - Robomimic
  - Franka
thumbnail: "/study-media/isaaclab-bc-franka/franka-stack-official.jpg"
---

## 들어가며

로봇에게 원하는 작업을 가르치는 방법에는 보상을 기반으로 시행착오를 반복하는 강화학습뿐 아니라, 사람이 수행한 성공 동작을 따라 배우는 **모방 학습(Imitation Learning)**도 있다. 이번 실습에서는 모방 학습의 가장 기본적인 방법인 **행동 복제(Behavior Cloning, BC)**를 이해하기 위해, NVIDIA Isaac Lab의 공식 Franka cube stacking 예제를 실행했다.

이번 글에서는 Isaac Sim 및 Isaac Lab 설치 과정은 제외하고, 다음 파이프라인을 직접 실행한 내용만 정리한다.

```text
공식 demonstration dataset 준비
→ Isaac Lab Mimic subtask annotation
→ Mimic 기반 추가 demonstration 생성
→ Robomimic Behavior Cloning 학습
→ epoch별 policy checkpoint 생성 확인
```

> 이 실습은 자체 task나 자체 데이터셋을 설계한 프로젝트가 아니라, 공식 예제를 이용해 imitation learning 파이프라인의 구조와 실행 흐름을 직접 확인한 기록이다.

---

## 1. 실습 대상: Franka Cube Stacking Task

이번 실습에서 사용한 환경은 다음과 같다.

```text
Isaac-Stack-Cube-Franka-IK-Rel-v0
```

이 환경에서는 Franka Panda 로봇팔이 세 개의 큐브를 순서대로 쌓는다. 최종 목표는 **파란색 큐브를 맨 아래에 두고, 그 위에 빨간색과 초록색 큐브를 순서대로 쌓는 것**이다.

![Isaac Lab Franka cube stacking 공식 예제 이미지](/study-media/isaaclab-bc-franka/franka-stack-official.jpg)

*그림 1. Isaac Lab 공식 문서에 제시된 Franka cube stacking 환경. 출처: NVIDIA Isaac Lab Documentation, “Available Environments”.*

작업은 다음과 같은 연속적인 로봇 manipulation 단계로 구성된다.

```text
1. 빨간색 큐브에 접근
2. 그리퍼로 빨간색 큐브 집기
3. 파란색 큐브 위로 이동
4. 빨간색 큐브 내려놓기
5. 초록색 큐브 집기
6. 빨간색 큐브 위에 올려놓기
```

단순히 로봇팔을 특정 위치로 보내는 문제가 아니라, **물체 접근 → grasp → transport → release**가 연속적으로 이어지는 task이므로 demonstration 기반 학습의 흐름을 확인하기 적합하다.

---

## 2. Behavior Cloning이란?

### 2.1 전문가의 행동을 정답으로 삼는 학습

행동 복제(Behavior Cloning, BC)는 전문가가 수행한 시연 데이터를 이용해, 현재 상태에서 전문가와 유사한 행동을 출력하도록 정책(policy)을 학습하는 방식이다.

로봇 시연 데이터는 보통 다음과 같은 시간 순서의 쌍으로 구성된다.

```text
D = {(oₜ, aₜ)}ₜ₌₀ᵀ
```

- `oₜ (observation)` : 시점 `t`에서 로봇과 객체의 상태
- `aₜ (action)` : 해당 상태에서 전문가가 수행한 행동

예를 들어 Franka가 빨간색 큐브를 집는 과정에서는 다음과 같은 데이터가 존재할 수 있다.

| 시점 | Observation 예시 | Expert Action 예시 |
|---|---|---|
| t=0 | 그리퍼가 빨간 큐브 왼쪽에 위치 | 오른쪽으로 이동 |
| t=1 | 그리퍼가 큐브 위에 위치 | 아래로 접근 |
| t=2 | grasp 가능한 위치에 도달 | 그리퍼 닫기 |
| t=3 | 큐브를 잡은 상태 | 파란 큐브 위로 이동 |
| t=4 | 목표 위치에 도달 | 그리퍼 열기 |

BC policy는 이러한 데이터에서 **“이 상태에서는 어떤 행동을 해야 하는가”**를 학습한다.

![Behavior Cloning 학습 흐름](/study-media/isaaclab-bc-franka/bc-workflow.svg)

*그림 2. 이번 실습에서 다룬 Behavior Cloning 파이프라인: 시연 데이터에서 Mimic 증강을 거쳐 BC-RNN policy checkpoint를 생성한다.*

### 2.2 목적 함수

정책을 \(\pi_\theta(a \mid o)\)라고 하면, BC는 전문가 데이터에 기록된 행동이 높은 확률로 출력되도록 파라미터 \(\theta\)를 학습한다. 일반적인 negative log-likelihood 형태의 손실은 다음과 같이 표현할 수 있다.

\[
\mathcal{L}_{BC}(\theta)
=
- \mathbb{E}_{(o,a) \sim D}
\left[
\log \pi_\theta(a \mid o)
\right]
\]

직관적으로는 다음과 같다.

```text
현재 상태 oₜ 입력
→ policy가 행동 âₜ 예측
→ 시연에 저장된 전문가 행동 aₜ와 비교
→ 전문가 행동과 가까워지도록 policy 업데이트
```

### 2.3 강화학습과의 차이

| 구분 | Behavior Cloning | Reinforcement Learning |
|---|---|---|
| 학습 신호 | 전문가 demonstration의 action | 환경에서 얻은 reward |
| 학습 방식 | 지도학습 | 시행착오 기반 최적화 |
| 장점 | 성공 시연이 있으면 빠르게 정책 학습 가능 | 사람이 모든 정답 동작을 보여주지 않아도 됨 |
| 주요 한계 | 시연 범위를 벗어난 상태에 취약할 수 있음 | 보상 설계와 탐색 비용이 큼 |

BC는 시연 데이터의 품질과 다양성에 매우 민감하다. 성공 demonstration이 충분히 다양하지 않다면, 학습된 로봇은 익숙하지 않은 초기 배치나 작은 오차가 발생한 상태에서 적절하게 복구하지 못할 수 있다.

---

## 3. Isaac Lab Mimic의 역할

행동 복제를 위해서는 성공 demonstration이 필요하지만, 사람이 직접 수많은 로봇 시연을 수집하는 것은 비용이 크다. **Isaac Lab Mimic**은 소수의 demonstration을 바탕으로 추가 demonstration을 자동 생성하는 기능이다.

중요한 점은 Mimic과 BC의 역할이 다르다는 것이다.

```text
Isaac Lab Mimic = 학습용 demonstration을 늘리는 데이터 생성 단계
Robomimic BC    = 생성된 demonstration으로 policy를 학습하는 단계
```

### 3.1 Subtask 기반 데이터 생성

Mimic은 하나의 긴 시연을 task의 의미 있는 구간, 즉 **subtask**로 나눈 뒤 각 구간을 새로운 객체 배치에 맞게 변환하고 연결한다.

Franka cube stacking의 예를 들면 다음과 같이 나눌 수 있다.

```text
빨간색 큐브 grasp
→ 빨간색 큐브 placement
→ 초록색 큐브 grasp
→ 초록색 큐브 placement
```

이후 큐브의 위치가 달라진 초기 상태에 맞춰 각 subtask trajectory를 변형하고 이어 붙여, BC 학습에 사용할 추가 demonstration을 만든다.

---

## 4. 공식 Demonstration Dataset 준비

이번 실습에서는 직접 teleoperation으로 시연을 수집하는 대신, Isaac Lab 공식 튜토리얼에서 제공하는 Franka cube stacking demonstration dataset을 사용했다. 공식 문서에 따르면 해당 dataset은 `Isaac-Stack-Cube-Franka-IK-Rel-v0` task의 **human demonstration 10개**를 포함한다.

```bash
cd ~/IsaacLab
mkdir -p datasets

wget -O ./datasets/dataset.hdf5 \
"https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/IsaacLab/Mimic/franka_stack_datasets/dataset.hdf5"

ls -lh ./datasets/dataset.hdf5
```

이 파일은 이후 annotation 및 Mimic 기반 데이터 생성의 입력으로 사용된다.

---

## 5. Mimic Subtask Annotation 수행

Mimic이 기존 demonstration을 변형하려면, 먼저 trajectory 내부에서 subtask가 완료되는 시점을 식별해야 한다. 공식 Franka 예제에는 자동 annotation을 위한 heuristic이 제공되므로 `--auto` 옵션을 사용했다.

```bash
cd ~/IsaacLab
conda activate env_isaaclab

export OMNI_KIT_ACCEPT_EULA=YES
export CUDA_VISIBLE_DEVICES=0

./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/annotate_demos.py \
  --headless \
  --device cpu \
  --task Isaac-Stack-Cube-Franka-IK-Rel-Mimic-v0 \
  --auto \
  --input_file ./datasets/dataset.hdf5 \
  --output_file ./datasets/annotated_dataset.hdf5
```

실행 결과, 공식 demonstration 10개가 모두 annotation되어 export되었고, 성공 task completion도 10개로 출력되었다.

![Isaac Lab Mimic annotation 결과](/study-media/isaaclab-bc-franka/mimic-annotation-complete.png)

*그림 3. `annotate_demos.py` 실행 결과. 10개의 annotated episode가 export되었고, successful task completion 역시 10개로 확인되었다.*

---

## 6. Mimic 기반 추가 Demonstration 생성

Annotation된 dataset을 바탕으로 Mimic을 사용해 추가 demonstration을 생성했다. 이번 실습은 학습 파이프라인의 실행 흐름을 확인하는 목적이었기 때문에, 대규모 dataset 생성 대신 소량의 trial만 실행했다.

```bash
cd ~/IsaacLab
conda activate env_isaaclab

export OMNI_KIT_ACCEPT_EULA=YES
export CUDA_VISIBLE_DEVICES=0

./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/generate_dataset.py \
  --headless \
  --device cpu \
  --num_envs 1 \
  --generation_num_trials 5 \
  --input_file ./datasets/annotated_dataset.hdf5 \
  --output_file ./datasets/generated_dataset_test.hdf5
```

| 인자 | 설정값 | 의미 |
|---|---:|---|
| `--device` | `cpu` | 소규모 I/O 중심 데이터 생성 단계이므로 CPU 모드 사용 |
| `--num_envs` | `1` | 동시에 실행하는 환경 수를 제한 |
| `--generation_num_trials` | `5` | 파이프라인 확인 목적의 소량 trial 생성 |
| `--input_file` | `annotated_dataset.hdf5` | subtask annotation이 반영된 입력 데이터 |
| `--output_file` | `generated_dataset_test.hdf5` | BC 학습에 사용할 생성 데이터 |

공식 문서에서는 더 안정적인 policy 학습 결과를 위해 더 많은 demonstration을 생성할 수 있음을 안내하지만, 이번 기록에서는 소량 데이터로 전체 파이프라인을 확인하는 데 초점을 맞췄다.

---

## 7. Robomimic Behavior Cloning 학습 실행

생성된 demonstration dataset을 이용해 Robomimic의 BC agent를 학습했다.

```bash
cd ~/IsaacLab
conda activate env_isaaclab

export OMNI_KIT_ACCEPT_EULA=YES
export CUDA_VISIBLE_DEVICES=0

./isaaclab.sh -p scripts/imitation_learning/robomimic/train.py \
  --task Isaac-Stack-Cube-Franka-IK-Rel-v0 \
  --algo bc \
  --dataset ./datasets/generated_dataset_test.hdf5
```

학습 경로명에서 확인할 수 있듯 이번 학습은 다음 설정으로 수행되었다.

```text
bc_rnn_low_dim_franka_stack
```

- `bc`: Behavior Cloning
- `rnn`: 이전 시점의 정보를 내부 상태에 반영하는 recurrent policy
- `low_dim`: 카메라 이미지가 아닌 저차원 상태 관측값 기반 policy
- `franka_stack`: Franka cube stacking task 대상

### 7.1 왜 RNN policy인가?

큐브 쌓기는 하나의 고정된 자세를 출력하는 문제가 아니라, 접근·집기·운반·배치의 순서가 이어지는 sequential manipulation task이다. 동일한 관측값처럼 보여도 이전에 큐브를 이미 집었는지, 놓으려는 중인지에 따라 다음 행동이 달라질 수 있다. 따라서 RNN 기반 policy는 직전 행동 흐름을 내부 상태에 반영할 수 있다는 점에서 이러한 조작 task에 적합하다.

### 7.2 학습 로그 확인

학습 도중에는 다음과 같은 지표들이 출력되었다.

| 로그 항목 | 의미 |
|---|---|
| `Log_Likelihood` | 시연 행동에 대해 policy가 부여하는 likelihood 관련 지표 |
| `Loss` | BC 학습 손실 |
| `Optimizer/policy0_lr` | policy optimizer의 learning rate |
| `Policy_Grad_Norms` | policy network gradient 크기 |
| `Time_Epoch` | 한 epoch 수행 시간 |
| `Memory Usage` | 학습 과정에서 사용된 메모리 |

![Robomimic BC-RNN 학습 로그](/study-media/isaaclab-bc-franka/bc-training-epoch-log.png)

*그림 4. `robomimic/train.py` 실행 중 출력된 BC-RNN 학습 로그. epoch별 loss와 memory usage가 출력되는 것을 확인할 수 있다.*

---

## 8. Checkpoint 생성 확인

학습 과정에서 일정 epoch마다 학습된 policy가 `.pth` 파일로 저장되었다. 다음 명령으로 생성된 checkpoint를 확인했다.

```bash
cd ~/IsaacLab

find logs/robomimic -name "*.pth" | sort
```

확인된 checkpoint 경로는 다음과 같다.

```text
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_100.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_200.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_300.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_400.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_500.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_600.pth
```

Checkpoint는 특정 epoch 시점의 policy parameter를 저장한 결과물이다. 예를 들어 `model_epoch_600.pth`는 600번째 epoch까지 학습된 BC-RNN policy를 의미한다.

모방 학습에서는 학습 epoch가 커질수록 항상 성능이 좋아진다고 단정할 수 없다. 데이터가 적거나 초기 상태의 다양성이 부족한 경우, 특정 demonstration에 과도하게 맞춰지는 과적합이 발생할 수 있기 때문이다. 따라서 실제 policy 평가 단계에서는 서로 다른 epoch의 checkpoint를 동일 조건에서 비교하는 것이 중요하다.

---

## 9. 이번 실습을 통해 정리한 핵심

### 9.1 BC는 demonstration action을 정답으로 사용하는 policy 학습이다

이번 과정에서 학습되는 것은 로봇의 직접적인 경로 계획 규칙이 아니라, 관측값을 입력받아 전문가 행동과 유사한 action을 출력하는 neural policy이다.

```text
Observation
→ BC-RNN Policy
→ Predicted Robot Action
```

### 9.2 Mimic과 BC는 서로 다른 단계이다

Mimic은 기존 시연을 subtask로 분리하고 변형하여 추가 데이터를 생성하는 역할을 한다. Robomimic BC는 그렇게 확보한 데이터를 바탕으로 실제 policy parameter를 학습한다.

```text
Mimic: 데이터 확장
BC:    policy 학습
```

### 9.3 소량 데이터 실습은 파이프라인 이해에 적합하다

이번 실습에서는 소량의 generated demonstration으로 학습을 실행했다. 이 설정은 높은 task 성공률을 목표로 하기보다는, demonstration annotation부터 policy checkpoint 저장까지 imitation learning의 전체 구성 요소를 직접 연결해보는 데 의미가 있다.

### 9.4 실제 학습 산출물은 checkpoint이다

학습 로그만 출력된 것이 아니라, epoch별 `.pth` policy checkpoint가 정상적으로 생성되었다. 즉, 공식 demonstration에서 출발해 Mimic 데이터 생성과 BC-RNN 학습까지 이어지는 학습 파이프라인이 실제로 수행되었음을 확인했다.

---

## 10. 실행 명령 전체 정리

### 10.1 공식 demonstration dataset 다운로드

```bash
cd ~/IsaacLab
mkdir -p datasets

wget -O ./datasets/dataset.hdf5 \
"https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/IsaacLab/Mimic/franka_stack_datasets/dataset.hdf5"
```

### 10.2 Subtask annotation

```bash
conda activate env_isaaclab
cd ~/IsaacLab

export OMNI_KIT_ACCEPT_EULA=YES
export CUDA_VISIBLE_DEVICES=0

./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/annotate_demos.py \
  --headless \
  --device cpu \
  --task Isaac-Stack-Cube-Franka-IK-Rel-Mimic-v0 \
  --auto \
  --input_file ./datasets/dataset.hdf5 \
  --output_file ./datasets/annotated_dataset.hdf5
```

### 10.3 Mimic 기반 추가 demonstration 생성

```bash
./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/generate_dataset.py \
  --headless \
  --device cpu \
  --num_envs 1 \
  --generation_num_trials 5 \
  --input_file ./datasets/annotated_dataset.hdf5 \
  --output_file ./datasets/generated_dataset_test.hdf5
```

### 10.4 Robomimic BC 학습

```bash
./isaaclab.sh -p scripts/imitation_learning/robomimic/train.py \
  --task Isaac-Stack-Cube-Franka-IK-Rel-v0 \
  --algo bc \
  --dataset ./datasets/generated_dataset_test.hdf5
```

### 10.5 생성된 checkpoint 확인

```bash
find logs/robomimic -name "*.pth" | sort
```

---

## 마무리

이번 실습에서는 Isaac Lab 공식 Franka cube stacking demonstration을 입력으로 사용해, **Mimic subtask annotation**, **추가 demonstration 생성**, 그리고 **Robomimic BC-RNN policy 학습 및 checkpoint 생성 확인**까지 수행했다.

이를 통해 행동 복제가 전문가의 시연을 정답으로 활용하는 지도학습 기반 policy 학습이라는 점, 그리고 Isaac Lab Mimic이 제한된 시연 데이터에서 추가 training data를 생성해 BC 학습을 지원하는 역할을 한다는 점을 확인할 수 있었다.

---

## 참고 자료

- [Isaac Lab Documentation — Teleoperation and Imitation Learning with Isaac Lab Mimic](https://isaac-sim.github.io/IsaacLab/main/source/overview/imitation-learning/teleop_imitation.html)
- [Isaac Lab Documentation — Available Environments](https://isaac-sim.github.io/IsaacLab/main/source/overview/environments.html)
- [Isaac Lab GitHub Repository](https://github.com/isaac-sim/IsaacLab)
- [Robomimic Documentation](https://robomimic.github.io/)
