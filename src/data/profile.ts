export const profile = {
  name: '이성민',
  englishName: 'Seongmin Lee',
  role: 'Mechanical Engineering Student · Robotics / Physical AI',
  university: 'Konkuk University',
  department: 'Mechanical & Aerospace Engineering',
  location: 'Seoul, Republic of Korea',
  email: 'lsm010711@naver.com',
  phone: '+82 10-3038-1872',
  showPhone: true,
  github: 'https://github.com/se0ngm1n',
  portfolio: 'https://se0ngm1n.com',
  image: {
    src: '/images/profile.jpg',
    alt: '이성민 프로필 사진',
  },
  resume: {
    available: false,
    href: '',
  },
  education: {
    school: 'Konkuk University',
    major: 'Mechanical & Aerospace Engineering',
    degree: 'B.S. Candidate',
    period: 'Mar. 2021 - Expected Mar. 2027',
  },
  awards: [
    '제5회 소방안전 빅데이터 플랫폼 활용 및 아이디어 경진대회 입선(장려상)',
    '건국대학교 교내 캡스톤디자인 경진대회 동상(4위)',
    '2025 한양대학교 창의적 종합설계 경진대회 우수상(2위)',
    '2025 국방 AI 경진대회 해커톤 (2박 3일) 해군 참모 총장상(우수상 3등)',
    '한국공과대학장협의회 (KEDC) 한국공과대학장협의회장상 수상',
    'DACON 스마트 창고 출고 지연 예측 AI 경진대회 607팀 중 33등, 상위 5.4%',
    '2026 AI ROOKIE 경진대회 100/721 (본선 진행중)',
  ],
  focusAreas: [
    'Physical AI',
    'Robotics',
    'Reinforcement Learning',
    'Robot Control',
    'Simulation-to-Real',
  ],
  navigationCards: [
    {
      title: 'Projects',
      description: 'Robotics, AI, embedded systems and prototype development',
      href: '/projects/',
    },
    {
      title: 'Study',
      description: 'Technical notes on simulation, reinforcement learning and robot control',
      href: '/study/',
    },
    {
      title: 'Life',
      description: 'Hiking, backpacking, camping and jiu-jitsu records',
      href: '/life/',
    },
  ],
};

export type Profile = typeof profile;
