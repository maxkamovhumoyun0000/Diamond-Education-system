## Deployment Guide

### Prerequisites
- GitHub repository connected
- Vercel project created
- Environment variables configured

### Environment Variables Required

**Backend (.env)**
```
DATABASE_URL=postgresql://user:password@host:5432/diamond_edu
JWT_SECRET=your_secret_key_min_32_chars
TELEGRAM_ADMIN_TOKEN=your_telegram_token
TELEGRAM_STUDENT_TOKEN=your_telegram_token
```

**Frontend (.env.local)**
```
NEXT_PUBLIC_API_BASE_URL=https://your-project.vercel.app
```

### Deployment Steps

1. **Push to GitHub**
```bash
git add .
git commit -m "Unified Diamond Education Platform"
git push origin main
```

2. **Configure Vercel Project**
- Go to Project Settings
- Select "Services" as Framework Preset
- Add Environment Variables from above
- Enable Deployment Protection if needed

3. **Deploy**
- Trigger deployment manually or via git push
- Vercel automatically detects multi-service setup
- Backend runs on port 3001
- Frontend runs on port 3000

### Post-Deployment

1. **Test Backend API**
   - Visit: `https://your-project.vercel.app/api/health`
   - Should return: `{"status": "healthy"}`

2. **Test Frontend**
   - Visit: `https://your-project.vercel.app`
   - Should display login page

3. **Configure Database**
   - Run SQL migrations in your PostgreSQL database
   - Execute scripts in order: `001_*.sql`, `002_*.sql`, etc.

4. **Telegram Bot Setup**
   - Update bot webhook URLs to point to backend
   - Configure admin and student tokens
   - Test bot commands

### Monitoring

- **Backend Logs**: Check Vercel Functions logs
- **Frontend Logs**: Browser console + Vercel deployment logs
- **Database**: Monitor PostgreSQL query performance
- **Bot**: Check Telegram bot updates via polling/webhook

### Troubleshooting

**API Returns 404**
- Verify Framework Preset is set to "Services"
- Check route prefix in vercel.json matches API calls

**Frontend Cannot Connect to Backend**
- Verify NEXT_PUBLIC_API_BASE_URL is correct
- Check CORS settings in FastAPI backend
- Verify backend service is running

**Database Errors**
- Verify DATABASE_URL is correct
- Check database credentials
- Ensure all migrations have run

**Bot Not Responding**
- Verify Telegram tokens are correct
- Check webhook URL is accessible
- Review bot error logs
