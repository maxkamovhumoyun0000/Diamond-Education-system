'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export type Language = 'uz' | 'ru' | 'en'

export const languages: { code: Language; name: string; flag: string }[] = [
  { code: 'uz', name: "O'zbekcha", flag: '🇺🇿' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
]

// Translations
export const translations: Record<Language, Record<string, string>> = {
  uz: {
    // Common
    'common.dashboard': 'Boshqaruv paneli',
    'common.login': 'Kirish',
    'common.logout': 'Chiqish',
    'common.settings': 'Sozlamalar',
    'common.search': 'Qidirish',
    'common.save': 'Saqlash',
    'common.cancel': 'Bekor qilish',
    'common.delete': 'O\'chirish',
    'common.edit': 'Tahrirlash',
    'common.add': 'Qo\'shish',
    'common.back': 'Orqaga',
    'common.next': 'Keyingi',
    'common.finish': 'Tugatish',
    'common.close': 'Yopish',
    'common.copy': 'Nusxalash',
    'common.copied': 'Nusxalandi!',
    'common.loading': 'Yuklanmoqda...',
    'common.error': 'Xatolik',
    'common.success': 'Muvaffaqiyat',
    'common.welcome': 'Xush kelibsiz',
    'common.articles': 'Maqolalar',
    'common.language': 'Til',
    
    // Roles
    'role.admin': 'Administrator',
    'role.student': "O'quvchi",
    'role.teacher': "O'qituvchi",
    'role.support': 'Yordam',
    
    // Subjects
    'subject.english': 'Ingliz tili',
    'subject.russian': 'Rus tili',
    'subject.select': 'Fan tanlang',
    
    // Login Page
    'login.title': 'Tizimga kirish',
    'login.subtitle': 'Diamond Education platformasiga xush kelibsiz',
    'login.email': 'Email yoki Login ID',
    'login.password': 'Parol',
    'login.remember': 'Meni eslab qol',
    'login.forgot': 'Parolni unutdingizmi?',
    'login.button': 'Kirish',
    'login.noAccount': "Hisobingiz yo'qmi?",
    'login.register': "Ro'yxatdan o'tish",
    'login.selectRole': 'Rolni tanlang',
    
    // Dashboard
    'dashboard.title': 'Boshqaruv paneli',
    'dashboard.welcome': 'Xush kelibsiz',
    
    // Admin
    'admin.users': 'Foydalanuvchilar',
    'admin.groups': 'Guruhlar',
    'admin.analytics': 'Tahlil',
    'admin.payments': "To'lovlar",
    'admin.aiGenerator': 'AI Generator',
    'admin.addUser': "Foydalanuvchi qo'shish",
    'admin.userManagement': 'Foydalanuvchilarni boshqarish',
    'admin.totalUsers': 'Jami foydalanuvchilar',
    
    // Add User Wizard
    'addUser.title': "Yangi foydalanuvchi qo'shish",
    'addUser.selectType': 'Foydalanuvchi turini tanlang',
    'addUser.newStudentTest': "Yangi o'quvchi (test bilan)",
    'addUser.existingStudent': "Mavjud o'quvchi (testsiz)",
    'addUser.teacher': "O'qituvchi",
    'addUser.support': 'Yordam xodimi',
    'addUser.enterInfo': "Ma'lumotlarni kiriting",
    'addUser.firstName': 'Ism',
    'addUser.lastName': 'Familiya',
    'addUser.phone': 'Telefon raqam',
    'addUser.selectSubject': 'Fan tanlang',
    'addUser.step': 'Qadam',
    'addUser.of': 'dan',
    'addUser.success': "Foydalanuvchi muvaffaqiyatli yaratildi!",
    'addUser.loginId': 'Login ID',
    'addUser.password': 'Parol',
    'addUser.oneTimePassword': "Bu bir martalik parol. Foydalanuvchi birinchi kirishda parolini o'zgartirishi kerak.",
    'addUser.copyCredentials': 'Login va parolni nusxalash',
    'addUser.addAnother': "Yana qo'shish",
    'addUser.backToPanel': 'Admin panelga qaytish',
    
    // Student
    'student.lessons': 'Darslar',
    'student.games': "O'yinlar",
    'student.vocabulary': "Lug'at",
    'student.leaderboard': 'Reyting',
    'student.homework': 'Uy vazifasi',
    'student.myLessons': 'Mening darslarim',
    'student.progress': 'Progress',
    
    // Teacher
    'teacher.myGroups': 'Mening guruhlarim',
    'teacher.attendance': 'Davomat',
    'teacher.tests': 'Testlar',
    
    // Lessons
    'lessons.fundamentals': 'Asoslar',
    'lessons.intermediate': "O'rta daraja",
    'lessons.advanced': 'Yuqori daraja',
    'lessons.special': 'Maxsus',
    'lessons.completed': 'Tugatildi',
    'lessons.inProgress': 'Davom etmoqda',
    'lessons.locked': 'Qulflangan',
    'lessons.continue': 'Davom etish',
    'lessons.review': "Ko'rib chiqish",
    'lessons.start': 'Boshlash',
    
    // Materials
    'materials.title': 'Materiallar',
    'materials.video': 'Video dars',
    'materials.audio': 'Audio',
    'materials.document': 'Hujjat',
    'materials.exercise': 'Mashq',
    'materials.grammar': 'Grammatika',
    'materials.vocabulary': "Lug'at",
    'materials.speaking': "So'zlashuv",
    'materials.listening': 'Tinglash',
    'materials.reading': "O'qish",
    'materials.writing': 'Yozish',
    
    // Status
    'status.active': 'Faol',
    'status.inactive': 'Nofaol',
    'status.pending': 'Kutilmoqda',
    
    // Support Booking
    'booking.title': 'Support Dars',
    'booking.heroTitle': "Qo'shimcha yordam kerakmi?",
    'booking.heroSubtitle': 'Support dars bron qiling',
    'booking.selectDate': 'Sanani tanlang',
    'booking.selectTime': 'Vaqtni tanlang',
    'booking.selectBranch': 'Filial',
    'booking.branch1': '1-filial',
    'booking.branch2': '2-filial',
    'booking.selectPurpose': 'Maqsad',
    'booking.speaking': "So'zlashuv amaliyoti",
    'booking.grammar': 'Grammatika',
    'booking.writing': 'Yozuv',
    'booking.reading': "O'qish",
    'booking.listening': 'Tinglash',
    'booking.general': 'Umumiy',
    'booking.bookLesson': 'Dars bron qilish',
    'booking.confirmation': 'Bron tasdiqlash',
    'booking.confirmBooking': 'Bronni tasdiqlash',
    'booking.myBookings': 'Mening bronlarim',
    'booking.upcoming': 'Kelayotgan',
    'booking.past': "O'tgan",
    'booking.pending': 'Kutilmoqda',
    'booking.approved': 'Tasdiqlangan',
    'booking.completed': 'Yakunlangan',
    'booking.cancelled': 'Bekor qilingan',
    'booking.reschedule': 'Qayta rejalashtirish',
    'booking.cancel': 'Bekor qilish',
    'booking.noBookings': 'Bronlar mavjud emas',
    'booking.available': 'Bo\'sh',
    'booking.blocked': 'Band',
    'booking.duration': '60 daqiqa',
    'booking.dcoinCost': "D'coin narxi",
    'booking.teacher': "O'qituvchi",
    'booking.success': 'Muvaffaqiyatli bron qilindi!',
    
    // Support Management
    'support.dashboard': 'Support panel',
    'support.todayBookings': 'Bugungi bronlar',
    'support.upcomingBookings': 'Kelayotgan bronlar',
    'support.totalThisMonth': 'Bu oydagi jami',
    'support.attendanceRate': 'Davomat foizi',
    'support.calendarManagement': 'Taqvim boshqaruvi',
    'support.allBookings': 'Barcha bronlar',
    'support.addSlot': "Vaqt qo'shish",
    'support.blockSlot': "Vaqtni bloklash",
    'support.closeDate': 'Sanani yopish',
    'support.markAttendance': 'Davomat belgilash',
    'support.giveBonus': 'Bonus berish',
    'support.present': 'Qatnashdi',
    'support.late': 'Kechikdi',
    'support.absent': "Kelmadi",
    'support.bonusReason': 'Bonus sababi',
    'support.settings': 'Sozlamalar',
    'support.defaultTimes': 'Standart vaqtlar',
    'support.bookingRules': 'Bron qoidalari',
    
    // Articles
    'articles.title': 'Maqolalar',
    'articles.create': 'Maqola yaratish',
    'articles.edit': 'Maqolani tahrirlash',
    'articles.delete': 'Maqolani o\'chirish',
    'articles.publish': 'Nashr qilish',
    'articles.unpublish': 'Nashrdan olish',
    'articles.draft': 'Qoralama',
    'articles.published': 'Nashr qilingan',
    'articles.allArticles': 'Barcha maqolalar',
    'articles.myArticles': 'Mening maqolalarim',
    'articles.permissions': 'Ruxsatlar',
    'articles.managePermissions': 'Ruxsatlarni boshqarish',
    'articles.allowCreate': 'Maqola yaratishga ruxsat',
    'articles.articleTitle': 'Maqola sarlavhasi',
    'articles.category': 'Kategoriya',
    'articles.featuredImage': 'Asosiy rasm',
    'articles.content': 'Matn',
    'articles.excerpt': 'Qisqa tavsif',
    'articles.tags': 'Teglar',
    'articles.visibility': 'Ko\'rinish',
    'articles.visibilityAll': 'Hammaga',
    'articles.visibilityStudents': 'Faqat o\'quvchilarga',
    'articles.visibilityTeachers': 'Faqat o\'qituvchilarga',
    'articles.metaTitle': 'Meta sarlavha (SEO)',
    'articles.metaDescription': 'Meta tavsif (SEO)',
    'articles.views': 'Ko\'rishlar',
    'articles.author': 'Muallif',
    'articles.readTime': 'O\'qish vaqti',
    'articles.minutes': 'daqiqa',
    'articles.noArticles': 'Maqolalar topilmadi',
    'articles.searchPlaceholder': 'Maqolalarni qidirish...',
    'articles.categories.grammar': 'Grammatika',
    'articles.categories.vocabulary': 'Lug\'at',
    'articles.categories.motivation': 'Motivatsiya',
    'articles.categories.tips': 'Maslahatlar',
    'articles.categories.culture': 'Madaniyat',
    'articles.categories.news': 'Yangiliklar',
    'articles.categories.general': 'Umumiy',
    
    // Internal Email
    'email.internal': 'Tizim email',
    'email.copyEmail': 'Emailni nusxalash',
  },
  ru: {
    // Common
    'common.dashboard': 'Панель управления',
    'common.login': 'Вход',
    'common.logout': 'Выход',
    'common.settings': 'Настройки',
    'common.search': 'Поиск',
    'common.save': 'Сохранить',
    'common.cancel': 'Отмена',
    'common.delete': 'Удалить',
    'common.edit': 'Редактировать',
    'common.add': 'Добавить',
    'common.back': 'Назад',
    'common.next': 'Далее',
    'common.finish': 'Завершить',
    'common.close': 'Закрыть',
    'common.copy': 'Копировать',
    'common.copied': 'Скопировано!',
    'common.loading': 'Загрузка...',
    'common.error': 'Ошибка',
    'common.success': 'Успех',
    'common.welcome': 'Добро пожаловать',
    'common.articles': 'Статьи',
    'common.language': 'Язык',
    
    // Roles
    'role.admin': 'Администратор',
    'role.student': 'Ученик',
    'role.teacher': 'Учитель',
    'role.support': 'Поддержка',
    
    // Subjects
    'subject.english': 'Английский язык',
    'subject.russian': 'Русский язык',
    'subject.select': 'Выберите предмет',
    
    // Login Page
    'login.title': 'Вход в систему',
    'login.subtitle': 'Добро пожаловать в Diamond Education',
    'login.email': 'Email или Login ID',
    'login.password': 'Пароль',
    'login.remember': 'Запомнить меня',
    'login.forgot': 'Забыли пароль?',
    'login.button': 'Войти',
    'login.noAccount': 'Нет аккаунта?',
    'login.register': 'Зарегистрироваться',
    'login.selectRole': 'Выберите роль',
    
    // Dashboard
    'dashboard.title': 'Панель управления',
    'dashboard.welcome': 'Добро пожаловать',
    
    // Admin
    'admin.users': 'Пользователи',
    'admin.groups': 'Группы',
    'admin.analytics': 'Аналитика',
    'admin.payments': 'Платежи',
    'admin.aiGenerator': 'AI Генератор',
    'admin.addUser': 'Добавить пользователя',
    'admin.userManagement': 'Управление пользователями',
    'admin.totalUsers': 'Всего пользователей',
    
    // Add User Wizard
    'addUser.title': 'Добавить нового пользователя',
    'addUser.selectType': 'Выберите тип пользователя',
    'addUser.newStudentTest': 'Новый ученик (с тестом)',
    'addUser.existingStudent': 'Существующий ученик (без теста)',
    'addUser.teacher': 'Учитель',
    'addUser.support': 'Сотрудник поддержки',
    'addUser.enterInfo': 'Введите данные',
    'addUser.firstName': 'Имя',
    'addUser.lastName': 'Фамилия',
    'addUser.phone': 'Номер телефона',
    'addUser.selectSubject': 'Выберите предмет',
    'addUser.step': 'Шаг',
    'addUser.of': 'из',
    'addUser.success': 'Пользователь успешно создан!',
    'addUser.loginId': 'Login ID',
    'addUser.password': 'Пароль',
    'addUser.oneTimePassword': 'Это одноразовый пароль. Пользователь должен сменить пароль при первом входе.',
    'addUser.copyCredentials': 'Копировать логин и пароль',
    'addUser.addAnother': 'Добавить ещё',
    'addUser.backToPanel': 'Вернуться в панель',
    
    // Student
    'student.lessons': 'Уроки',
    'student.games': 'Игры',
    'student.vocabulary': 'Словарь',
    'student.leaderboard': 'Рейтинг',
    'student.homework': 'Домашнее задание',
    'student.myLessons': 'Мои уроки',
    'student.progress': 'Прогресс',
    
    // Teacher
    'teacher.myGroups': 'Мои группы',
    'teacher.attendance': 'Посещаемость',
    'teacher.tests': 'Тесты',
    
    // Lessons
    'lessons.fundamentals': 'Основы',
    'lessons.intermediate': 'Средний уровень',
    'lessons.advanced': 'Продвинутый',
    'lessons.special': 'Специальный',
    'lessons.completed': 'Завершено',
    'lessons.inProgress': 'В процессе',
    'lessons.locked': 'Заблокировано',
    'lessons.continue': 'Продолжить',
    'lessons.review': 'Просмотреть',
    'lessons.start': 'Начать',
    
    // Materials
    'materials.title': 'Материалы',
    'materials.video': 'Видео урок',
    'materials.audio': 'Аудио',
    'materials.document': 'Документ',
    'materials.exercise': 'Упражнение',
    'materials.grammar': 'Грамматика',
    'materials.vocabulary': 'Словарь',
    'materials.speaking': 'Разговор',
    'materials.listening': 'Аудирование',
    'materials.reading': 'Чтение',
    'materials.writing': 'Письмо',
    
    // Status
    'status.active': 'Активен',
    'status.inactive': 'Неактивен',
    'status.pending': 'Ожидает',
    
    // Support Booking
    'booking.title': 'Support урок',
    'booking.heroTitle': 'Нужна дополнительная помощь?',
    'booking.heroSubtitle': 'Забронируйте Support урок',
    'booking.selectDate': 'Выберите дату',
    'booking.selectTime': 'Выберите время',
    'booking.selectBranch': 'Филиал',
    'booking.branch1': 'Филиал 1',
    'booking.branch2': 'Филиал 2',
    'booking.selectPurpose': 'Цель',
    'booking.speaking': 'Практика разговора',
    'booking.grammar': 'Грамматика',
    'booking.writing': 'Письмо',
    'booking.reading': 'Чтение',
    'booking.listening': 'Аудирование',
    'booking.general': 'Общее',
    'booking.bookLesson': 'Забронировать урок',
    'booking.confirmation': 'Подтверждение брони',
    'booking.confirmBooking': 'Подтвердить бронь',
    'booking.myBookings': 'Мои брони',
    'booking.upcoming': 'Предстоящие',
    'booking.past': 'Прошедшие',
    'booking.pending': 'Ожидает',
    'booking.approved': 'Подтверждено',
    'booking.completed': 'Завершено',
    'booking.cancelled': 'Отменено',
    'booking.reschedule': 'Перенести',
    'booking.cancel': 'Отменить',
    'booking.noBookings': 'Нет бронирований',
    'booking.available': 'Свободно',
    'booking.blocked': 'Занято',
    'booking.duration': '60 минут',
    'booking.dcoinCost': "Стоимость D'coin",
    'booking.teacher': 'Учитель',
    'booking.success': 'Успешно забронировано!',
    
    // Support Management
    'support.dashboard': 'Панель Support',
    'support.todayBookings': 'Брони сегодня',
    'support.upcomingBookings': 'Предстоящие брони',
    'support.totalThisMonth': 'Всего в этом месяце',
    'support.attendanceRate': 'Процент посещаемости',
    'support.calendarManagement': 'Управление календарём',
    'support.allBookings': 'Все брони',
    'support.addSlot': 'Добавить время',
    'support.blockSlot': 'Заблокировать время',
    'support.closeDate': 'Закрыть дату',
    'support.markAttendance': 'Отметить посещаемость',
    'support.giveBonus': 'Дать бонус',
    'support.present': 'Присутствовал',
    'support.late': 'Опоздал',
    'support.absent': 'Отсутствовал',
    'support.bonusReason': 'Причина бонуса',
    'support.settings': 'Настройки',
    'support.defaultTimes': 'Стандартное время',
    'support.bookingRules': 'Правила бронирования',
    
    // Articles
    'articles.title': 'Статьи',
    'articles.create': 'Создать статью',
    'articles.edit': 'Редактировать статью',
    'articles.delete': 'Удалить статью',
    'articles.publish': 'Опубликовать',
    'articles.unpublish': 'Снять с публикации',
    'articles.draft': 'Черновик',
    'articles.published': 'Опубликовано',
    'articles.allArticles': 'Все статьи',
    'articles.myArticles': 'Мои статьи',
    'articles.permissions': 'Разрешения',
    'articles.managePermissions': 'Управление разрешениями',
    'articles.allowCreate': 'Разрешить создание статей',
    'articles.articleTitle': 'Заголовок статьи',
    'articles.category': 'Категория',
    'articles.featuredImage': 'Главное изображение',
    'articles.content': 'Содержание',
    'articles.excerpt': 'Краткое описание',
    'articles.tags': 'Теги',
    'articles.visibility': 'Видимость',
    'articles.visibilityAll': 'Для всех',
    'articles.visibilityStudents': 'Только для учеников',
    'articles.visibilityTeachers': 'Только для учителей',
    'articles.metaTitle': 'Мета заголовок (SEO)',
    'articles.metaDescription': 'Мета описание (SEO)',
    'articles.views': 'Просмотры',
    'articles.author': 'Автор',
    'articles.readTime': 'Время чтения',
    'articles.minutes': 'минут',
    'articles.noArticles': 'Статьи не найдены',
    'articles.searchPlaceholder': 'Поиск статей...',
    'articles.categories.grammar': 'Грамматика',
    'articles.categories.vocabulary': 'Словарь',
    'articles.categories.motivation': 'Мотивация',
    'articles.categories.tips': 'Советы',
    'articles.categories.culture': 'Культура',
    'articles.categories.news': 'Новости',
    'articles.categories.general': 'Общее',
    
    // Internal Email
    'email.internal': 'Системный email',
    'email.copyEmail': 'Копировать email',
  },
  en: {
    // Common
    'common.dashboard': 'Dashboard',
    'common.login': 'Login',
    'common.logout': 'Logout',
    'common.settings': 'Settings',
    'common.search': 'Search',
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.add': 'Add',
    'common.back': 'Back',
    'common.next': 'Next',
    'common.finish': 'Finish',
    'common.close': 'Close',
    'common.copy': 'Copy',
    'common.copied': 'Copied!',
    'common.loading': 'Loading...',
    'common.error': 'Error',
    'common.success': 'Success',
    'common.welcome': 'Welcome',
    'common.articles': 'Articles',
    'common.language': 'Language',
    
    // Roles
    'role.admin': 'Administrator',
    'role.student': 'Student',
    'role.teacher': 'Teacher',
    'role.support': 'Support',
    
    // Subjects
    'subject.english': 'English',
    'subject.russian': 'Russian',
    'subject.select': 'Select subject',
    
    // Login Page
    'login.title': 'Sign In',
    'login.subtitle': 'Welcome to Diamond Education platform',
    'login.email': 'Email or Login ID',
    'login.password': 'Password',
    'login.remember': 'Remember me',
    'login.forgot': 'Forgot password?',
    'login.button': 'Sign In',
    'login.noAccount': "Don't have an account?",
    'login.register': 'Register',
    'login.selectRole': 'Select role',
    
    // Dashboard
    'dashboard.title': 'Dashboard',
    'dashboard.welcome': 'Welcome',
    
    // Admin
    'admin.users': 'Users',
    'admin.groups': 'Groups',
    'admin.analytics': 'Analytics',
    'admin.payments': 'Payments',
    'admin.aiGenerator': 'AI Generator',
    'admin.addUser': 'Add User',
    'admin.userManagement': 'User Management',
    'admin.totalUsers': 'Total Users',
    
    // Add User Wizard
    'addUser.title': 'Add New User',
    'addUser.selectType': 'Select user type',
    'addUser.newStudentTest': 'New Student (with test)',
    'addUser.existingStudent': 'Existing Student (no test)',
    'addUser.teacher': 'Teacher',
    'addUser.support': 'Support Staff',
    'addUser.enterInfo': 'Enter information',
    'addUser.firstName': 'First Name',
    'addUser.lastName': 'Last Name',
    'addUser.phone': 'Phone Number',
    'addUser.selectSubject': 'Select Subject',
    'addUser.step': 'Step',
    'addUser.of': 'of',
    'addUser.success': 'User created successfully!',
    'addUser.loginId': 'Login ID',
    'addUser.password': 'Password',
    'addUser.oneTimePassword': 'This is a one-time password. User must change password on first login.',
    'addUser.copyCredentials': 'Copy login and password',
    'addUser.addAnother': 'Add Another',
    'addUser.backToPanel': 'Back to Admin Panel',
    
    // Student
    'student.lessons': 'Lessons',
    'student.games': 'Games',
    'student.vocabulary': 'Vocabulary',
    'student.leaderboard': 'Leaderboard',
    'student.homework': 'Homework',
    'student.myLessons': 'My Lessons',
    'student.progress': 'Progress',
    
    // Teacher
    'teacher.myGroups': 'My Groups',
    'teacher.attendance': 'Attendance',
    'teacher.tests': 'Tests',
    
    // Lessons
    'lessons.fundamentals': 'Fundamentals',
    'lessons.intermediate': 'Intermediate',
    'lessons.advanced': 'Advanced',
    'lessons.special': 'Special',
    'lessons.completed': 'Completed',
    'lessons.inProgress': 'In Progress',
    'lessons.locked': 'Locked',
    'lessons.continue': 'Continue',
    'lessons.review': 'Review',
    'lessons.start': 'Start',
    
    // Materials
    'materials.title': 'Materials',
    'materials.video': 'Video Lesson',
    'materials.audio': 'Audio',
    'materials.document': 'Document',
    'materials.exercise': 'Exercise',
    'materials.grammar': 'Grammar',
    'materials.vocabulary': 'Vocabulary',
    'materials.speaking': 'Speaking',
    'materials.listening': 'Listening',
    'materials.reading': 'Reading',
    'materials.writing': 'Writing',
    
    // Status
    'status.active': 'Active',
    'status.inactive': 'Inactive',
    'status.pending': 'Pending',
    
    // Support Booking
    'booking.title': 'Support Lesson',
    'booking.heroTitle': 'Need extra help?',
    'booking.heroSubtitle': 'Book a Support Lesson',
    'booking.selectDate': 'Select Date',
    'booking.selectTime': 'Select Time',
    'booking.selectBranch': 'Branch',
    'booking.branch1': 'Branch 1',
    'booking.branch2': 'Branch 2',
    'booking.selectPurpose': 'Purpose',
    'booking.speaking': 'Speaking Practice',
    'booking.grammar': 'Grammar',
    'booking.writing': 'Writing',
    'booking.reading': 'Reading',
    'booking.listening': 'Listening',
    'booking.general': 'General',
    'booking.bookLesson': 'Book Lesson',
    'booking.confirmation': 'Booking Confirmation',
    'booking.confirmBooking': 'Confirm Booking',
    'booking.myBookings': 'My Bookings',
    'booking.upcoming': 'Upcoming',
    'booking.past': 'Past',
    'booking.pending': 'Pending',
    'booking.approved': 'Approved',
    'booking.completed': 'Completed',
    'booking.cancelled': 'Cancelled',
    'booking.reschedule': 'Reschedule',
    'booking.cancel': 'Cancel',
    'booking.noBookings': 'No bookings yet',
    'booking.available': 'Available',
    'booking.blocked': 'Blocked',
    'booking.duration': '60 minutes',
    'booking.dcoinCost': "D'coin Cost",
    'booking.teacher': 'Teacher',
    'booking.success': 'Successfully booked!',
    
    // Support Management
    'support.dashboard': 'Support Dashboard',
    'support.todayBookings': 'Today\'s Bookings',
    'support.upcomingBookings': 'Upcoming Bookings',
    'support.totalThisMonth': 'Total This Month',
    'support.attendanceRate': 'Attendance Rate',
    'support.calendarManagement': 'Calendar Management',
    'support.allBookings': 'All Bookings',
    'support.addSlot': 'Add Time Slot',
    'support.blockSlot': 'Block Slot',
    'support.closeDate': 'Close Date',
    'support.markAttendance': 'Mark Attendance',
    'support.giveBonus': 'Give Bonus',
    'support.present': 'Present',
    'support.late': 'Late',
    'support.absent': 'Absent',
    'support.bonusReason': 'Bonus Reason',
    'support.settings': 'Settings',
    'support.defaultTimes': 'Default Times',
    'support.bookingRules': 'Booking Rules',
  },
}

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: string) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>('uz')

  useEffect(() => {
    // Load language from localStorage on mount
    const savedLang = localStorage.getItem('diamond-language') as Language
    if (savedLang && ['uz', 'ru', 'en'].includes(savedLang)) {
      setLanguageState(savedLang)
    }
  }, [])

  const setLanguage = (lang: Language) => {
    setLanguageState(lang)
    localStorage.setItem('diamond-language', lang)
  }

  const t = (key: string): string => {
    return translations[language][key] || key
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}
