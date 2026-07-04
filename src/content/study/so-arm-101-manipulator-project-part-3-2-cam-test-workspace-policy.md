---
title: "[SO-ARM 101 Manipulator Project Part 3] 2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민"
date: 2026-07-03
category: "Study"
summary: "Wrist CAM과 Overview CAM을 함께 사용하는 2-camera dataset을 구축하고, ACT와 Diffusion Policy를 동일 조건에서 학습한 뒤 Test Workspace 기반 평가 구조를 정리"
tags:
  - "SO-ARM 101"
  - "LeRobot"
  - "Behavior Cloning"
  - "Imitation Learning"
  - "ACT"
  - "Pick and Place"
thumbnail: "/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-47.png"
---

## 내용 요약

이전 포스팅에서 1차 테스트를 완료한 뒤 데이터를 300개 정도 더 수집했지만, 생각보다 성능 개선이 크게 일어나지 않았다. 입력이 카메라 1개뿐이었고, Wrist CAM의 시야각이 좁아서 한정적인 영역에서만 큐브 집기에 성공했다. 특히 initial point에서 policy가 처음 관측하는 이미지에 큐브가 명확히 보이는지가 rollout 성능에 큰 영향을 준다고 판단했다.

따라서 이번 포스팅에서는 아래 내용을 진행했다.

1. Wrist CAM과 Overview CAM을 함께 사용하는 2-CAM 환경 세팅
2. 2-camera 1-cube pick-and-place-home dataset 200 episodes 구축
3. 동일 dataset 기준으로 ACT Policy와 Diffusion Policy를 각각 40k step 학습
4. 성능 평가를 위한 camera-aware Test Workspace 지정
5. trial 시작 조건을 통제하기 위한 Enter-trigger 기반 rollout 실행 구조 준비
6. 향후 350 episodes 확장, policy 비교, hyperparameter 조정 계획 정리

## 1. 2-CAM 환경 세팅

Wrist CAM의 시야각이 생각보다 좁아서 하나만으로는 넓은 영역에 포진해 있는 큐브를 집기가 쉽지 않았다. 게다가 그리퍼와 로봇팔이 물체를 가리는 경우가 있었고, 큐브가 initial observation에서 명확히 보이지 않으면 policy가 첫 접근 방향부터 흔들리는 문제가 있었다.

다른 SO-ARM101 프로젝트를 찾아봐도 대부분 2-CAM 환경으로 구성하고 있었다. 따라서 기존 Wrist CAM에 더해 책상 전체를 내려다보는 Overview CAM을 추가했다. Overview CAM은 큐브의 전역 위치를 넓게 관측하고, Wrist CAM은 물체에 가까워졌을 때의 국소적인 접근 정보를 제공하는 역할을 기대했다.

![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/img-3187.jpg)

다음과 같이 Overview CAM 세팅을 하였다.

<video controls preload="metadata" playsinline>
  <source src="/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/image.mov" type="video/quicktime" />
</video>

처음에는 70개 정도의 데이터를 수집해 ACT로 빠르게 학습을 진행했다. 이 테스트만으로도 이전 1-CAM, 400 data 환경보다 더 안정적인 모습을 보여주었다. 이 결과를 보고 단순히 데이터 수만 늘리는 것보다 observation 구조를 먼저 개선하는 것이 더 중요하다고 판단했다.

## 2. 2-camera dataset 구축

기존에는 Wrist CAM 중심으로 데이터를 수집했지만, 그리퍼와 로봇팔이 물체를 가리는 문제가 있었다. 특히 policy가 rollout을 시작하는 initial point에서 큐브가 관측 이미지 안에 명확히 보이는지가 성능에 큰 영향을 주었다.

이를 개선하기 위해 Wrist CAM과 Overview CAM을 동시에 입력으로 사용하는 2-camera dataset을 새로 구축했다. 사용한 입력 feature는 다음과 같다.

```text
observation.images.overview
observation.images.wrist
observation.state
action
```

수집한 dataset 구성은 다음과 같다.

```text
Dataset: so101_cube1_pick_place_2cam_200_v1
Task: 1-cube pick-and-place-home
Episodes: 200
Camera input: overview camera + wrist camera
Action: 6-DoF joint action
Task description:
Pick the visible wooden cube and place it into the box, then return the arm to the home position.
```

각 episode는 다음 흐름으로 구성했다.

```text
1. 큐브 1개를 책상 위에 배치
2. 로봇팔이 큐브를 집음
3. 박스에 큐브를 넣음
4. 로봇팔이 initial/home position으로 복귀
5. episode 종료
```

여기서 중요한 점은 단순히 큐브를 집어 넣는 것에서 끝내지 않고, 항상 home position으로 복귀하도록 episode 구조를 통일했다는 것이다. 이후 rollout을 반복 평가할 때 각 trial이 동일한 initial condition에서 시작되도록 하기 위함이다.

행동복제에서는 episode의 끝 상태도 다음 실험 구조에 영향을 준다. 큐브를 넣은 직후 로봇팔이 애매한 위치에 남아 있으면 다음 trial의 시작 조건이 흔들리고, policy 평가 결과를 비교하기 어려워진다. 그래서 이번 dataset부터는 pick-and-place-home을 하나의 완결된 task로 정의했다.

## 3. ACT와 Diffusion Policy 학습

2-camera dataset을 수집한 뒤, 같은 dataset을 기준으로 두 가지 policy를 학습했다.

```text
1. ACT Policy
2. Diffusion Policy
```

ACT는 기존 실험에서도 사용했던 baseline policy이다. 현재 observation을 바탕으로 이후 action chunk를 직접 예측하는 방식이기 때문에 비교적 빠르고, 실시간 rollout에 적용하기 좋다. 이전 Part 2와 1-CAM 실험에서도 ACT를 먼저 사용했기 때문에, observation 구조를 바꿨을 때의 차이를 보기에도 적합했다.

반면 Diffusion Policy는 action trajectory를 denoising 과정을 통해 생성하는 방식이다. 더 복잡한 action distribution을 표현할 가능성이 있지만, 학습과 추론 속도는 ACT보다 무거울 수 있다. 면접 피드백에서도 policy를 바꿔 비교해보고 이후 hyperparameter를 조정해보면 기술면접에서 좋은 실험이 될 수 있다는 조언을 받았다. 그래서 이번 단계에서는 ACT와 Diffusion을 동일 dataset 기준으로 비교하기로 했다.

현재까지 진행한 학습은 다음과 같다.

```text
ACT:
Dataset: so101_cube1_pick_place_2cam_200_v1
Steps: 40k
Status: training completed

Diffusion Policy:
Dataset: so101_cube1_pick_place_2cam_200_v1
Steps: 40k
Status: training completed
```

아직 이 단계에서는 정식 rollout 평가는 수행하지 않았고, 학습만 완료한 상태이다. 바로 성공률을 말하기보다는, 먼저 평가 workspace와 trial 실행 방식을 고정한 뒤 같은 조건에서 비교하려고 한다.

## 4. Test Workspace 지정

앞으로 체계화된 성능 평가를 위해 Test Workspace를 지정했고, 세부적인 평가 방법은 계속 고도화할 예정이다. 이번에는 로봇암이 실제로 도달할 수 있는 영역, Overview CAM의 시야 영역, Wrist CAM의 시야 영역을 함께 고려했다.

### Wrist CAM 좌우 가시 영역 확인
![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-01.png)

Wrist CAM에 큐브가 보이지 않는 좌우 한계선을 측정했다. 이 과정에서 카메라의 fish-eye 현상이 생각보다 심하다는 것을 알게 되었다. Check board calibration을 진행할까도 고민했지만, 이번 실험에서는 큐브의 정확한 위치 좌표를 직접 뽑는 것이 아니라 image observation 기반 policy를 학습하는 것이 목적이므로 일단 스킵했다.

### Wrist CAM 상단 가시 한계선 확인
![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-08.png)

좌우 가시 영역과 상단 가시 한계선을 연필로 옅게 책상에 표시해 두었다.

### Overview CAM 가시 영역 확인
![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-16.png)

Overview CAM에서 큐브가 통에 가려지는 부분과 그림자에 의해 가려지는 영역을 확인했다. 이 영역은 어차피 로봇의 Wrist CAM과 박스가 부딪혀 접근하기 어려운 영역이므로 추가적인 표시는 하지 않았다.

### Test Workspace 정하기
![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-25.png)

Wrist CAM과 Overview CAM의 가시 영역을 합치면 다음과 같다.

![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-39.png)

Wrist CAM과 로봇암의 workspace를 표시한 모습이다.

![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-47.png)

모든 영역을 합치면 다음과 같다.

![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-35-11.png)

평가 영역은 크게 영역 1(Wrist + Overview)과 영역 2(Overview 중심)로 나누었다. 영역 1은 두 카메라 모두 큐브를 비교적 안정적으로 관측할 수 있는 구간이고, 영역 2는 Wrist CAM에서는 제한적이지만 Overview CAM이 전역 위치를 제공할 수 있는 구간이다. 이후 성공률을 단일 숫자로만 보지 않고, 어느 가시성 조건에서 실패가 발생하는지 나누어 보려고 한다.

## 5. Enter-trigger 기반 rollout 실행 코드 준비

기존 rollout은 policy가 계속 실행되는 구조였다. 로봇이 큐브를 집어 박스에 넣고 home position으로 돌아온 뒤에도 policy가 계속 카메라 입력을 보고 있었다.

이 상태에서 다음 큐브를 책상에 올리면, policy가 새로운 큐브를 바로 인식해버리고 다음 trial이 의도하지 않게 시작되는 문제가 있었다. 이 문제를 줄이기 위해 Enter 키를 기준으로 rollout을 시작하거나 중단할 수 있는 실행 구조를 준비했다.

목표한 사용 흐름은 다음과 같다.

```text
1. 사용자가 큐브를 test workspace 안에 배치
2. 손을 카메라 화면 밖으로 뺌
3. Enter 입력
4. policy rollout 시작
5. 로봇이 pick-and-place-home 수행
6. 다시 Enter 입력
7. rollout 중단 및 reset
8. 다음 trial 준비
```

아직 이 코드를 이용해 정식 rollout 평가는 수행하지 않았지만, 추후 성능 평가에서 각 trial의 시작 조건을 통제하기 위해 사용할 예정이다.

이 방식의 목적은 다음과 같다.

```text
- trial 사이에 policy가 계속 실행되는 문제 방지
- 큐브를 새로 배치하는 동안 로봇이 반응하지 않도록 제어
- 각 trial을 명확한 initial observation에서 시작
- ACT와 Diffusion을 동일한 평가 조건에서 비교
```

실제 로봇 실험에서는 모델 성능뿐 아니라 평가 절차도 결과에 영향을 준다. 큐브를 올리는 사람의 손이 카메라에 남아 있거나, reset 중에 policy가 계속 action을 내보내면 trial 사이 조건이 달라진다. Enter-trigger 구조는 이런 변수를 줄이기 위한 최소한의 장치다.

## 6. 앞으로의 진행 방향

앞에서 정의한 camera-aware Test Workspace를 바탕으로, 다음 단계에서는 정확한 성능 평가 기준을 설정할 예정이다.

단순히 전체 성공률만 보는 것이 아니라, 큐브 위치와 카메라 가시성 조건에 따라 성능을 나눠서 평가할 계획이다. 예를 들어 다음과 같은 기준을 사용할 수 있다.

```text
Position condition:
- 중앙 영역
- 왼쪽 영역
- 오른쪽 영역
- 먼 영역
- workspace boundary 근처
- box 근처

Camera visibility condition:
- overview camera와 wrist camera 모두 잘 보이는 영역
- overview camera 위주로만 잘 보이는 영역
- wrist camera 위주로만 잘 보이는 영역
- wrist camera에서 가림이 발생하는 영역

Failure type:
- 허공 집기
- 큐브를 밀고 지나감
- 파지 실패
- 박스 투입 실패
- home 복귀 불안정
- rollout latency 또는 control loop 지연
```

이 기준을 바탕으로 ACT 200ep 모델과 Diffusion 200ep 모델을 각각 rollout 해보고, 동일한 Test Workspace에서 성공률과 실패 유형을 비교할 예정이다.

이후에는 데이터를 약 150 episodes 정도 더 수집해 총 350 episodes 수준의 2-camera dataset으로 확장할 계획이다. 추가 데이터는 현재 모델이 약한 위치나 실패가 자주 발생하는 조건을 중심으로 수집할 예정이다.

예상되는 다음 dataset 구성은 다음과 같다.

```text
Current dataset:
2-camera 1-cube pick-and-place-home: 200 episodes

Additional dataset:
2-camera additional data: about 150 episodes

Total:
about 350 episodes
```

추가 데이터 수집 후에는 동일하게 ACT와 Diffusion Policy를 다시 학습하고, 이전 200 episode 모델과 성능을 비교할 것이다. 이를 통해 단순히 policy 차이만 보는 것이 아니라, 데이터 양 증가가 성능에 어떤 영향을 주는지도 함께 확인할 수 있다.

최종 단계에서는 더 좋은 성능을 보인 policy를 기준으로 hyperparameter를 조정할 계획이다. ACT의 경우 다음과 같은 parameter를 조정할 수 있다.

```text
- training steps
- chunk size
- learning rate
- batch size
- temporal ensemble 관련 설정
```

Diffusion Policy의 경우 다음과 같은 parameter를 조정할 수 있다.

```text
- denoising inference steps
- prediction horizon
- action horizon
- learning rate
- batch size
```

최종 목표는 다음과 같다.

```text
1. 2-camera observation이 기존 wrist-only observation보다 안정적인지 확인
2. ACT와 Diffusion Policy의 성능 차이를 동일 dataset 기준으로 비교
3. 데이터 양 증가에 따른 성능 변화를 확인
4. Test Workspace 기반으로 위치별/가시성별 실패 유형 분석
5. 가장 좋은 policy에 대해 hyperparameter를 조정해 최종 성능 개선
```

이 과정을 통해 단순히 "행동복제 모델을 돌려봤다"가 아니라, 관측 구조, dataset scale, policy type, hyperparameter가 실제 robot manipulation 성능에 어떤 영향을 주는지 단계적으로 분석하는 실험으로 발전시키고자 한다.
