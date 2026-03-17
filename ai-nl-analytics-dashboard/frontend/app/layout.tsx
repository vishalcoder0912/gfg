import './globals.css'
import { IBM_Plex_Sans, Space_Grotesk } from 'next/font/google'

const fontBody = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-body',
})

const fontDisplay = Space_Grotesk({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-display',
})

export const metadata = {
  title: 'AI Analytics Dashboard',
  description: 'AI-powered data analytics dashboard',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${fontBody.variable} ${fontDisplay.variable} font-body`}>
        {children}
      </body>
    </html>
  )
}
