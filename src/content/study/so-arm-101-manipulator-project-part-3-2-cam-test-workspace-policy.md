---
title: "[SO-ARM 101 Manipulator Project Part 3] 2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민"
date: 2026-07-03
category: "Study"
summary: "Wrist CAM, Overview CAM 세팅 후 데이터 수집과, Policy와, 파라미터 값 수정 대한 고민을 진행. Test Workspace 세팅 완료, 추후 성능 평가 진행 환경 구축"
tags:
  - "SO-ARM 101"
  - "LeRobot"
  - "Behavior Cloning"
  - "Imitation Learning"
  - "ACT"
  - "Pick and Place"
thumbnail: "/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-47.png"
---

##내용 요약
이전 포스팅 1차 테스트 완료 후 데이터를 300개 정도 더 수집하였으나, 생각보다 성능 개선이 크게 일어나지 않았다. 또한 입력이 카메라 1개 뿐이고, Wrist CAM 의 시야각이 너무 좁아서 생각보다 한정적인 영역에서만 큐브 집기에 성공하였다. 따라서 이번 포스팅에서는 아래와 같은 내용을 진행하였다.

1. Wrist CAM , Overview CAM 의 2CAM 환경으로 세팅
2. 2CAM 환경에서 데이터 수집, 이때 ACT, Diffusion 정책 두 가지 경우에 대해 학습 진행 후 성능 비교. 어느정도 성능이 나오는 Best 정책에 대해 파라미터 조정까지 진행해보는 것을 목표로 한다.
3. 이때 '성능' 에 대한 객관적 기준점을 잡기 위해 Test Workspace를 정하기 -> 로봇암의 Workspace, Overview CAM 시야 영역, Wrist CAM 시야 영역 을 고려하여 학습을 진행하고, 평가를 진행할 Workspace를 설정

## 1. 2CAM 환경 세팅
Wrist CAM의 시야각이 생각보다 좁아서 하나만으로는 넓은 영역에 포진해 있는 큐브를 집기가 쉽지 않다. 다른 분들 프로젝트를 찾아보니 모두 2CAM 환경으로 세팅하였다. OVerview CAM의 추가로 큐브의 위치를 넓게 식별하고, 큐브 접근 정확도 또한 높아질 것이다.

![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/img-3187.jpg)

다음과 같이 Overview CAM 세팅을 하였다.

<video controls preload="metadata" playsinline>
  <source src="/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/image.mov" type="video/quicktime" />
</video>

처음에 70개의 데이터 수집을 했고, ACT로 정책 학습을 진행하였다. 이전 1CAM, 400데이터 환경보다 훨씬 좋은 성능을 보여주었다.

## 2 ACT, Diffusion 학습 진행

(이곳에 작성)

##3 Test Workspace 지정
앞으로 체계화된 성능 평가를 위해 Test Wrokspace를 지정하였고, 세부적인 평가 방법은 고도화 해나갈 예정이다.

###Wrist CAM 좌우 가시 영역 확인
![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-01.png)
Wrist CAM에 큐브가 보이지 않는 좌우 한계선을 정확히 측정하였다. 이 과정에서 카메라의 Fish eye 현상이 생각보다 심하다는 것을 알게 되었다. Check Board Calibration을 진행할까도 고민해보았지만, 우리가 큐브의 정확한 위치 좌표를 뽑을 예정은 아니므로 일단 스킵하도록한다.

###Wrist CAM 상단 가시 한계선 확인
![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-08.png)

좌우 가시 영역과, 상단 가시 한계선을 연필로 옅게 책상에 표시해 두었다.

###Overview CAM 가시 영역 확인
![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-16.png)
Overview CAM이 보았을 때 큐브가 통에 가려지는 부분과 그림자에 의해 가려지는 영역이다. 어차피 로봇의 Wrist CAM 과 박스가 부딫혀 접근할 수 없는 영역이므로 추가적인 표시는 하지 않았다.

###Test Wrokspace 정하기
![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-25.png)
Wrist CAM 과 Overview CAM의 가시 영역을 합치면 다음과 같다.

![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-39.png)
Wrist CAM 과 로봇암의 Workspace를 표시한 모습

![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-23-47.png)
모든 영역을 합치면 다음과 같다.

![ SO-ARM 101 Manipulator Project Part 3  2-CAM 환경 구축, Test Workspace 세팅, 데이터 수집과 Policy에 대한 고민](/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/2026-07-04-1-35-11.png)
평가 영역을 영역1 (Wrist + Overview)과 영역2(Overview만)로 나누었다

##추후 진행 방향
