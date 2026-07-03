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
thumbnail: ""
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

처음에 70개의 데이터 수집을 했고, 이전 1CAM, 400데이터 환경보다 훨씬 좋은 성능을 보여줌을 확인하였다.

<video controls preload="metadata" playsinline>
  <source src="/study-media/so-arm-101-manipulator-project-part-3-2-cam-test-workspace-policy/image.mov" type="video/quicktime" />
</video>
