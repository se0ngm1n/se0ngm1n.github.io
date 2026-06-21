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

## 다음 단계

다음 진행할거 -> 행동복제학습 데이터 수집하고 픽앤플레이스 구현

다음 단계에서는 물체의 초기 위치와 조명, 접근 방향을 바꾸어 여러 차례 시연 데이터를 수집할 예정이다. 먼저 고정된 작업대에서 단일 물체를 집어 지정 위치로 옮기는 Pick & Place를 구현하고, 성공률과 실패 원인을 기록해 데이터 품질과 정책의 일반화 성능을 개선한다.

이후 진행 계획은 다음과 같다.

1. 카메라 영상과 리더·팔로워 암의 관절 상태를 동기화해 시연 데이터 수집
2. 행동복제 정책을 학습하고 고정 환경에서 Pick & Place 성공률 평가
3. AnySkin 센서를 그리퍼에 장착해 접촉 및 미끄러짐 정보를 관측값에 추가
4. LeKiwi 이동 플랫폼과 통합해 이동 후 물체를 탐색하고 파지하는 전체 작업 구현
