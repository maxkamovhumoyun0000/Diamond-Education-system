'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useLanguage } from '@/lib/i18n'
import { 
  Play, 
  FileText, 
  Headphones, 
  BookOpen, 
  PenTool, 
  MessageSquare,
  Lock,
  CheckCircle,
  Clock,
  ChevronRight
} from 'lucide-react'

type Subject = 'english' | 'russian'
type MaterialType = 'video' | 'audio' | 'document' | 'exercise'

interface Material {
  id: string
  title: string
  titleRu: string
  titleUz: string
  type: MaterialType
  duration?: string
  completed: boolean
  locked: boolean
  category: string
  categoryRu: string
  categoryUz: string
}

const englishMaterials: Material[] = [
  // Grammar
  { id: 'e1', title: 'Present Simple Tense', titleRu: 'Настоящее простое время', titleUz: 'Oddiy hozirgi zamon', type: 'video', duration: '15 min', completed: true, locked: false, category: 'Grammar', categoryRu: 'Грамматика', categoryUz: 'Grammatika' },
  { id: 'e2', title: 'Present Continuous', titleRu: 'Настоящее продолженное время', titleUz: 'Davomli hozirgi zamon', type: 'video', duration: '18 min', completed: true, locked: false, category: 'Grammar', categoryRu: 'Грамматика', categoryUz: 'Grammatika' },
  { id: 'e3', title: 'Past Simple Tense', titleRu: 'Прошедшее простое время', titleUz: "Oddiy o'tgan zamon", type: 'video', duration: '20 min', completed: false, locked: false, category: 'Grammar', categoryRu: 'Грамматика', categoryUz: 'Grammatika' },
  { id: 'e4', title: 'Future Tenses', titleRu: 'Будущие времена', titleUz: 'Kelasi zamonlar', type: 'video', duration: '25 min', completed: false, locked: true, category: 'Grammar', categoryRu: 'Грамматика', categoryUz: 'Grammatika' },
  
  // Vocabulary
  { id: 'e5', title: 'Daily Routine Words', titleRu: 'Слова о распорядке дня', titleUz: 'Kundalik tartib so\'zlari', type: 'document', completed: true, locked: false, category: 'Vocabulary', categoryRu: 'Словарный запас', categoryUz: "Lug'at" },
  { id: 'e6', title: 'Food & Drinks', titleRu: 'Еда и напитки', titleUz: "Ovqat va ichimliklar", type: 'document', completed: false, locked: false, category: 'Vocabulary', categoryRu: 'Словарный запас', categoryUz: "Lug'at" },
  { id: 'e7', title: 'Travel Vocabulary', titleRu: 'Туристический словарь', titleUz: "Sayohat lug'ati", type: 'document', completed: false, locked: true, category: 'Vocabulary', categoryRu: 'Словарный запас', categoryUz: "Lug'at" },
  
  // Listening
  { id: 'e8', title: 'Podcast: Daily Conversations', titleRu: 'Подкаст: Ежедневные разговоры', titleUz: 'Podkast: Kundalik suhbatlar', type: 'audio', duration: '12 min', completed: true, locked: false, category: 'Listening', categoryRu: 'Аудирование', categoryUz: 'Tinglash' },
  { id: 'e9', title: 'News Report Practice', titleRu: 'Практика новостных репортажей', titleUz: 'Yangiliklar amaliyoti', type: 'audio', duration: '10 min', completed: false, locked: false, category: 'Listening', categoryRu: 'Аудирование', categoryUz: 'Tinglash' },
  
  // Exercises
  { id: 'e10', title: 'Grammar Quiz: Tenses', titleRu: 'Тест по грамматике: Времена', titleUz: 'Grammatika testi: Zamonlar', type: 'exercise', duration: '15 min', completed: false, locked: false, category: 'Exercises', categoryRu: 'Упражнения', categoryUz: 'Mashqlar' },
  { id: 'e11', title: 'Writing Practice', titleRu: 'Практика письма', titleUz: 'Yozuv mashqlari', type: 'exercise', duration: '20 min', completed: false, locked: true, category: 'Exercises', categoryRu: 'Упражнения', categoryUz: 'Mashqlar' },
]

const russianMaterials: Material[] = [
  // Grammar
  { id: 'r1', title: 'Russian Alphabet', titleRu: 'Русский алфавит', titleUz: 'Rus alifbosi', type: 'video', duration: '20 min', completed: true, locked: false, category: 'Grammar', categoryRu: 'Грамматика', categoryUz: 'Grammatika' },
  { id: 'r2', title: 'Noun Cases Introduction', titleRu: 'Введение в падежи', titleUz: 'Kelishiklar kirish', type: 'video', duration: '25 min', completed: true, locked: false, category: 'Grammar', categoryRu: 'Грамматика', categoryUz: 'Grammatika' },
  { id: 'r3', title: 'Verb Conjugation', titleRu: 'Спряжение глаголов', titleUz: "Fe'l tuslanishi", type: 'video', duration: '22 min', completed: false, locked: false, category: 'Grammar', categoryRu: 'Грамматика', categoryUz: 'Grammatika' },
  { id: 'r4', title: 'Adjective Agreement', titleRu: 'Согласование прилагательных', titleUz: 'Sifat moslashuvi', type: 'video', duration: '18 min', completed: false, locked: true, category: 'Grammar', categoryRu: 'Грамматика', categoryUz: 'Grammatika' },
  
  // Vocabulary
  { id: 'r5', title: 'Family Members', titleRu: 'Члены семьи', titleUz: 'Oila a\'zolari', type: 'document', completed: true, locked: false, category: 'Vocabulary', categoryRu: 'Словарный запас', categoryUz: "Lug'at" },
  { id: 'r6', title: 'Numbers & Counting', titleRu: 'Числа и счёт', titleUz: "Raqamlar va hisoblash", type: 'document', completed: false, locked: false, category: 'Vocabulary', categoryRu: 'Словарный запас', categoryUz: "Lug'at" },
  { id: 'r7', title: 'Colors & Shapes', titleRu: 'Цвета и формы', titleUz: "Ranglar va shakllar", type: 'document', completed: false, locked: true, category: 'Vocabulary', categoryRu: 'Словарный запас', categoryUz: "Lug'at" },
  
  // Listening
  { id: 'r8', title: 'Russian Songs for Beginners', titleRu: 'Русские песни для начинающих', titleUz: 'Boshlang\'ichlar uchun rus qo\'shiqlari', type: 'audio', duration: '15 min', completed: true, locked: false, category: 'Listening', categoryRu: 'Аудирование', categoryUz: 'Tinglash' },
  { id: 'r9', title: 'Dialogue Practice', titleRu: 'Практика диалогов', titleUz: 'Dialog amaliyoti', type: 'audio', duration: '10 min', completed: false, locked: false, category: 'Listening', categoryRu: 'Аудирование', categoryUz: 'Tinglash' },
  
  // Exercises
  { id: 'r10', title: 'Case Endings Quiz', titleRu: 'Тест по падежным окончаниям', titleUz: 'Kelishik qo\'shimchalari testi', type: 'exercise', duration: '15 min', completed: false, locked: false, category: 'Exercises', categoryRu: 'Упражнения', categoryUz: 'Mashqlar' },
  { id: 'r11', title: 'Verb Conjugation Practice', titleRu: 'Практика спряжения глаголов', titleUz: 'Fe\'l tuslanish mashqi', type: 'exercise', duration: '20 min', completed: false, locked: true, category: 'Exercises', categoryRu: 'Упражнения', categoryUz: 'Mashqlar' },
]

export default function MaterialsPage() {
  const { t, language } = useLanguage()
  const [selectedSubject, setSelectedSubject] = useState<Subject>('english')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  const materials = selectedSubject === 'english' ? englishMaterials : russianMaterials

  const categories = ['all', ...Array.from(new Set(materials.map(m => m.category)))]

  const filteredMaterials = selectedCategory === 'all' 
    ? materials 
    : materials.filter(m => m.category === selectedCategory)

  const getTitle = (material: Material) => {
    if (language === 'ru') return material.titleRu
    if (language === 'uz') return material.titleUz
    return material.title
  }

  const getCategory = (material: Material) => {
    if (language === 'ru') return material.categoryRu
    if (language === 'uz') return material.categoryUz
    return material.category
  }

  const getCategoryLabel = (cat: string) => {
    if (cat === 'all') return language === 'uz' ? 'Barchasi' : language === 'ru' ? 'Все' : 'All'
    const material = materials.find(m => m.category === cat)
    if (material) return getCategory(material)
    return cat
  }

  const getTypeIcon = (type: MaterialType) => {
    switch (type) {
      case 'video': return <Play size={20} />
      case 'audio': return <Headphones size={20} />
      case 'document': return <FileText size={20} />
      case 'exercise': return <PenTool size={20} />
    }
  }

  const getTypeLabel = (type: MaterialType) => {
    switch (type) {
      case 'video': return t('materials.video')
      case 'audio': return t('materials.audio')
      case 'document': return t('materials.document')
      case 'exercise': return t('materials.exercise')
    }
  }

  const completedCount = materials.filter(m => m.completed).length
  const progress = Math.round((completedCount / materials.length) * 100)

  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">{t('materials.title')}</h1>
          <p className="text-text-secondary">{completedCount} / {materials.length} {t('lessons.completed').toLowerCase()}</p>
        </div>

        {/* Subject Tabs */}
        <div className="flex gap-4">
          <button
            onClick={() => { setSelectedSubject('english'); setSelectedCategory('all') }}
            className={`flex items-center gap-3 px-6 py-4 rounded-xl border-2 transition-all ${
              selectedSubject === 'english'
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50 bg-surface'
            }`}
          >
            <span className="text-2xl">🇬🇧</span>
            <div className="text-left">
              <p className="font-semibold text-text-primary">{t('subject.english')}</p>
              <p className="text-xs text-text-secondary">{englishMaterials.filter(m => m.completed).length}/{englishMaterials.length}</p>
            </div>
          </button>
          <button
            onClick={() => { setSelectedSubject('russian'); setSelectedCategory('all') }}
            className={`flex items-center gap-3 px-6 py-4 rounded-xl border-2 transition-all ${
              selectedSubject === 'russian'
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50 bg-surface'
            }`}
          >
            <span className="text-2xl">🇷🇺</span>
            <div className="text-left">
              <p className="font-semibold text-text-primary">{t('subject.russian')}</p>
              <p className="text-xs text-text-secondary">{russianMaterials.filter(m => m.completed).length}/{russianMaterials.length}</p>
            </div>
          </button>
        </div>

        {/* Progress Bar */}
        <div className="bg-surface border border-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-3">
            <span className="font-medium text-text-primary">{t('student.progress')}</span>
            <span className="text-primary font-semibold">{progress}%</span>
          </div>
          <div className="h-3 bg-surface-hover rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Category Filters */}
        <div className="flex gap-2 flex-wrap">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                selectedCategory === cat
                  ? 'bg-primary text-white'
                  : 'bg-surface border border-border text-text-primary hover:border-primary'
              }`}
            >
              {getCategoryLabel(cat)}
            </button>
          ))}
        </div>

        {/* Materials Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredMaterials.map((material) => (
            <div
              key={material.id}
              className={`rounded-xl border p-5 transition-all ${
                material.locked
                  ? 'bg-surface-hover border-border opacity-60'
                  : material.completed
                  ? 'bg-green-500/5 border-green-500/30'
                  : 'bg-surface border-border hover:border-primary hover:shadow-lg'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={`p-3 rounded-lg ${
                  material.locked ? 'bg-surface' : material.completed ? 'bg-green-500/10' : 'bg-primary/10'
                }`}>
                  {material.locked ? (
                    <Lock size={20} className="text-text-secondary" />
                  ) : (
                    <span className={material.completed ? 'text-green-500' : 'text-primary'}>
                      {getTypeIcon(material.type)}
                    </span>
                  )}
                </div>
                {material.completed && (
                  <CheckCircle size={24} className="text-green-500" />
                )}
              </div>

              <h3 className="font-semibold text-text-primary mb-2">{getTitle(material)}</h3>
              
              <div className="flex items-center gap-3 text-sm text-text-secondary mb-4">
                <span className="px-2 py-1 rounded bg-surface-hover">{getTypeLabel(material.type)}</span>
                {material.duration && (
                  <span className="flex items-center gap-1">
                    <Clock size={14} />
                    {material.duration}
                  </span>
                )}
              </div>

              <button
                disabled={material.locked}
                className={`w-full py-2.5 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
                  material.locked
                    ? 'bg-surface text-text-secondary cursor-not-allowed'
                    : material.completed
                    ? 'bg-green-500/10 text-green-600 hover:bg-green-500/20'
                    : 'bg-primary text-white hover:bg-primary-dark'
                }`}
              >
                {material.locked && t('lessons.locked')}
                {material.completed && t('lessons.review')}
                {!material.locked && !material.completed && (
                  <>
                    {t('lessons.start')}
                    <ChevronRight size={18} />
                  </>
                )}
              </button>
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  )
}
