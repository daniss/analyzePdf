'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, AlertCircle } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'

export default function SignUpPage() {
  const { register, loading, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [localError, setLocalError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')
    
    if (password !== confirmPassword) {
      setLocalError('Les mots de passe ne correspondent pas')
      return
    }

    if (password.length < 8) {
      setLocalError('Le mot de passe doit contenir au moins 8 caractères')
      return
    }
    
    try {
      await register(email, password, companyName || undefined)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Registration failed'
      setLocalError(errorMessage)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <FileText className="h-10 w-10 text-primary" />
          </div>
          <CardTitle className="text-2xl">Créer un compte</CardTitle>
          <CardDescription>
            Commencez votre essai gratuit avec 5 factures par mois
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {(localError || error) && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm">{localError || error}</span>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                placeholder="nom@exemple.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="company">Nom de l'entreprise (Optionnel)</Label>
              <Input
                id="company"
                type="text"
                placeholder="Entreprise SARL"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirmer le mot de passe</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Création du compte...' : "S'inscrire"}
            </Button>
            <p className="text-sm text-center text-muted-foreground">
              Vous avez déjà un compte ?{' '}
              <Link href="/auth/signin" className="text-primary hover:underline">
                Se connecter
              </Link>
            </p>
            <p className="text-xs text-center text-muted-foreground">
              En vous inscrivant, vous acceptez nos{' '}
              <Link href="/terms" className="underline">
                Conditions d'utilisation
              </Link>{' '}
              et notre{' '}
              <Link href="/privacy" className="underline">
                Politique de confidentialité
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}