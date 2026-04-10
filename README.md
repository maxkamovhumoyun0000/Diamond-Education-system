# Diamond Education Admin Panel

A comprehensive admin control panel for managing students, articles, groups, and the D'coin reward system for the Diamond Education platform.

## Features

### 🎓 Student Management
- Add and manage students (regular and support types)
- Track student levels (A1-C2 IELTS levels)
- Assign students to groups
- Monitor student attendance and progress

### 📚 Articles Management
- Create and publish educational articles
- Control article visibility (Teachers, Support Teachers, Students)
- Organize articles by subject and level
- Rich text editing capabilities

### 👥 Group Management
- Create study groups with subject and level specifications
- Assign teachers to groups
- Manage student enrollment in groups
- Track group progress and attendance

### 💰 D'Coin System
- Digital reward currency for student motivation
- Track D'coin balances and transactions
- Award coins for achievements and participation
- Deduct coins for policy violations
- View transaction history

### 💬 Internal Communication
- Send messages between staff members
- Create notifications for system events
- Manage communication logs

## Technology Stack

- **Frontend**: Next.js 16, React 19, TypeScript
- **Styling**: Tailwind CSS with custom design tokens
- **Database**: Supabase PostgreSQL with Row Level Security
- **Authentication**: Supabase Auth with JWT sessions
- **Deployment**: Vercel

## Project Structure

```
diamond-education-admin/
├── app/
│   ├── auth/
│   │   ├── login/page.tsx
│   │   ├── sign-up/page.tsx
│   │   ├── callback/route.ts
│   │   └── error/page.tsx
│   ├── dashboard/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── students/page.tsx
│   │   ├── articles/page.tsx
│   │   ├── groups/page.tsx
│   │   ├── dcoin/page.tsx
│   │   └── messages/page.tsx
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── lib/
│   └── supabase/
│       ├── client.ts
│       ├── server.ts
│       └── middleware.ts
├── scripts/
│   ├── 001_init_profiles.sql
│   ├── 002_subjects_levels.sql
│   ├── 003_groups.sql
│   ├── 004_articles.sql
│   ├── 005_dcoin.sql
│   └── 006_messages.sql
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── postcss.config.js
└── package.json
```

## Getting Started

### Prerequisites

- Node.js 18+
- Supabase account with PostgreSQL database
- Environment variables configured in Vercel

### Environment Variables

Create a `.env.local` file with:

```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

Visit `http://localhost:3000` to see the application.

## Database Setup

The project includes SQL migration scripts to set up the database schema:

1. **001_init_profiles.sql** - User profiles and enums
2. **002_subjects_levels.sql** - Subjects and IELTS levels
3. **003_groups.sql** - Study groups and student assignments
4. **004_articles.sql** - Educational articles with permissions
5. **005_dcoin.sql** - D'coin transactions and balances
6. **006_messages.sql** - Internal messaging and notifications

Run these migrations in your Supabase SQL editor to initialize the database.

## User Roles

- **Super Admin**: Full system access
- **Admin**: Administrative functions
- **Teacher**: Teaching and content creation
- **Support Teacher**: Support and assistance
- **Student**: Learning and D'coin management

## Key Components

### Authentication
- Email/password authentication with Supabase
- JWT-based session management
- Automatic profile creation on signup
- Middleware-based route protection

### Dashboard
- Responsive layout with sidebar navigation
- Quick action buttons
- System statistics cards
- User profile management

### Pages
- **Students**: CRUD operations for student records
- **Articles**: Article creation with permission controls
- **Groups**: Group management and student enrollment
- **D'Coin**: Transaction management and balance tracking
- **Messages**: Internal communication system

## Design System

### Colors
- **Primary**: Navy Blue (#1e3a8a)
- **Secondary**: Gold (#fbbf24)
- **Accent**: Light Blue (#3b82f6)
- **Neutral**: Grays and whites

### Typography
- Sans-serif for body and UI
- Font weights: 400, 500, 600, 700
- Line height: 1.4-1.6 for body text

## Security Features

- Row Level Security (RLS) on all database tables
- JWT-based authentication
- Secure session management with HTTP-only cookies
- Protected API routes
- Input validation and sanitization

## Development

### Code Style
- TypeScript for type safety
- ESLint for code quality
- Tailwind CSS for styling
- Component-based architecture

### Best Practices
- Server-side rendering where possible
- Client-side hydration for interactive features
- Optimistic updates for better UX
- Error boundary implementation

## Deployment

The project is configured for deployment on Vercel:

```bash
# Deploy to Vercel
vercel deploy
```

## Future Enhancements

- [ ] Real-time updates with WebSockets
- [ ] File uploads for student documents
- [ ] Advanced analytics dashboard
- [ ] Email notifications integration
- [ ] Mobile application
- [ ] Video content support
- [ ] AI-powered student recommendations
- [ ] Integration with payment systems

## Support

For issues and questions, please contact the development team or create an issue in the repository.

## License

Proprietary - Diamond Education System
