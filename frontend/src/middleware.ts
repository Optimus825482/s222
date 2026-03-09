import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Backend URL - runtime'da environment variable'dan al
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // /api/* isteklerini backend'e proxy
  if (pathname.startsWith('/api/')) {
    const targetUrl = `${BACKEND_URL}${pathname}${request.nextUrl.search}`
    
    return NextResponse.rewrite(new URL(targetUrl))
  }

  // /ws/* isteklerini backend'e proxy
  if (pathname.startsWith('/ws/')) {
    const targetUrl = `${BACKEND_URL}${pathname}${request.nextUrl.search}`
    
    return NextResponse.rewrite(new URL(targetUrl))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/api/:path*', '/ws/:path*'],
}