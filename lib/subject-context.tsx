'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export type Subject = 'english' | 'russian'

export interface SubjectData {
  dcoins: number
  level: number
  xp: number
  xpToNextLevel: number
  streak: number
  lessonsCompleted: number
  vocabularyLearned: number
  testsCompleted: number
  rank: number
}

interface SubjectContextType {
  subject: Subject
  setSubject: (subject: Subject) => void
  subjectData: Record<Subject, SubjectData>
  currentSubjectData: SubjectData
  addDcoins: (amount: number) => void
  addXp: (amount: number) => void
}

const defaultSubjectData: Record<Subject, SubjectData> = {
  english: {
    dcoins: 1250,
    level: 12,
    xp: 4500,
    xpToNextLevel: 5000,
    streak: 7,
    lessonsCompleted: 42,
    vocabularyLearned: 320,
    testsCompleted: 8,
    rank: 23,
  },
  russian: {
    dcoins: 850,
    level: 8,
    xp: 2800,
    xpToNextLevel: 3500,
    streak: 3,
    lessonsCompleted: 28,
    vocabularyLearned: 180,
    testsCompleted: 5,
    rank: 45,
  },
}

const SubjectContext = createContext<SubjectContextType | undefined>(undefined)

export function SubjectProvider({ children }: { children: ReactNode }) {
  const [subject, setSubjectState] = useState<Subject>('english')
  const [subjectData, setSubjectData] = useState<Record<Subject, SubjectData>>(defaultSubjectData)

  useEffect(() => {
    // Load subject from localStorage on mount
    const savedSubject = localStorage.getItem('diamond-subject') as Subject
    if (savedSubject && ['english', 'russian'].includes(savedSubject)) {
      setSubjectState(savedSubject)
    }
    
    // Load subject data from localStorage
    const savedData = localStorage.getItem('diamond-subject-data')
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData)
        setSubjectData(parsed)
      } catch {
        // Use default data
      }
    }
  }, [])

  const setSubject = (newSubject: Subject) => {
    setSubjectState(newSubject)
    localStorage.setItem('diamond-subject', newSubject)
  }

  const addDcoins = (amount: number) => {
    setSubjectData(prev => {
      const updated = {
        ...prev,
        [subject]: {
          ...prev[subject],
          dcoins: prev[subject].dcoins + amount,
        },
      }
      localStorage.setItem('diamond-subject-data', JSON.stringify(updated))
      return updated
    })
  }

  const addXp = (amount: number) => {
    setSubjectData(prev => {
      const currentData = prev[subject]
      let newXp = currentData.xp + amount
      let newLevel = currentData.level
      let newXpToNext = currentData.xpToNextLevel

      // Level up if XP exceeds threshold
      while (newXp >= newXpToNext) {
        newXp -= newXpToNext
        newLevel++
        newXpToNext = Math.floor(newXpToNext * 1.2) // 20% more XP needed each level
      }

      const updated = {
        ...prev,
        [subject]: {
          ...currentData,
          xp: newXp,
          level: newLevel,
          xpToNextLevel: newXpToNext,
        },
      }
      localStorage.setItem('diamond-subject-data', JSON.stringify(updated))
      return updated
    })
  }

  const currentSubjectData = subjectData[subject]

  return (
    <SubjectContext.Provider value={{ 
      subject, 
      setSubject, 
      subjectData, 
      currentSubjectData,
      addDcoins,
      addXp,
    }}>
      {children}
    </SubjectContext.Provider>
  )
}

export function useSubject() {
  const context = useContext(SubjectContext)
  if (context === undefined) {
    throw new Error('useSubject must be used within a SubjectProvider')
  }
  return context
}
