// Demo accounts for the prototype. Passwords are stored as a simple hash
// (see services/auth.js) so they are not sitting in plain text. This is NOT
// real security; it exists to show how login and role routing work.
import { demoHash } from '../hash.js'

const u = (id, name, email, password, role, extra = {}) => ({
  id,
  name,
  email,
  passwordHash: demoHash(password),
  role,
  ...extra,
})

export const users = [
  // Students
  u('u-meera', 'Meera Iyer', 'meera.iyer@gradient.edu', 'student123', 'student', { studentId: 'GU-24-0112', program: 'B.Sc. Computer Science', year: 'Year 1' }),
  u('u-fatima', 'Fatima Khan', 'fatima.khan@gradient.edu', 'student123', 'student', { studentId: 'GU-24-0231', program: 'B.Sc. Computer Science', year: 'Year 1' }),
  u('u-daniel', 'Daniel Okafor', 'daniel.okafor@gradient.edu', 'student123', 'student', { studentId: 'GU-23-0408', program: 'B.Tech. Information Technology', year: 'Year 2' }),
  u('u-sofia', 'Sofia Alvarez', 'sofia.alvarez@gradient.edu', 'student123', 'student', { studentId: 'GU-24-0377', program: 'B.Sc. Computer Science', year: 'Year 1' }),
  u('u-kenji', 'Kenji Watanabe', 'kenji.watanabe@gradient.edu', 'student123', 'student', { studentId: 'GU-23-0519', program: 'B.A. Economics', year: 'Year 2' }),
  u('u-priya', 'Priya Nair', 'priya.nair@gradient.edu', 'student123', 'student', { studentId: 'GU-23-0290', program: 'B.Tech. Information Technology', year: 'Year 2' }),
  u('u-lucas', 'Lucas Meyer', 'lucas.meyer@gradient.edu', 'student123', 'student', { studentId: 'GU-24-0455', program: 'B.Sc. Engineering', year: 'Year 1' }),
  // Faculty
  u('u-rao', 'Dr. Ananya Rao', 'ananya.rao@gradient.edu', 'faculty123', 'faculty', { title: 'Associate Professor', department: 'Computer Science' }),
  u('u-lee', 'Prof. Marcus Lee', 'marcus.lee@gradient.edu', 'faculty123', 'faculty', { title: 'Professor', department: 'Economics' }),
  // Management
  u('u-hale', 'Prof. Richard Hale', 'richard.hale@gradient.edu', 'admin123', 'admin', { title: 'Dean of Academic Affairs', department: 'Office of the Dean' }),
]

/** Shown on the login screen so reviewers can try each role quickly. */
export const demoLogins = [
  { portal: 'student', name: 'Meera Iyer', note: 'Mid-way through a plan', email: 'meera.iyer@gradient.edu', password: 'student123' },
  { portal: 'student', name: 'Fatima Khan', note: 'New student, no courses yet', email: 'fatima.khan@gradient.edu', password: 'student123' },
  { portal: 'staff', name: 'Dr. Ananya Rao', note: 'Faculty · Computer Science', email: 'ananya.rao@gradient.edu', password: 'faculty123' },
  { portal: 'staff', name: 'Prof. Richard Hale', note: 'Management · Dean', email: 'richard.hale@gradient.edu', password: 'admin123' },
]
