export const profile = {
  name: '이성민',
  englishName: 'Seongmin Lee',
  role: 'Mechanical Engineering Student · Robotics / Physical AI',
  university: 'Konkuk University',
  department: 'Mechanical & Aerospace Engineering',
  location: 'Seoul, Republic of Korea',
  email: 'lsm010711**@naver.com',
  phone: '+82 10-3038-1872',
  showPhone: true,
  github: 'https://github.com/se0ngm1n',
  portfolio: 'https://se0ngm1n.com',
  image: {
    src: '/images/profile.png',
    alt: 'Seongmin Lee profile photo',
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
    '2025 Defense AI Competition, Chief of Naval Operations Award · 3rd Place',
    '2025 Hanyang University Creative Integrated Design Competition · 2nd Place',
    '2025 Konkuk University Capstone Design Competition · 4th Place',
    'Korean Engineering Deans Council Award',
  ],
  focusAreas: ['Physical AI', 'Robotics', 'Autonomous Driving'],
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
