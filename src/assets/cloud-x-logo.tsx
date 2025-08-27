import React from 'react'

interface CloudXLogoProps {
  className?: string
  width?: number
  height?: number
}

export function CloudXLogo({ className = '', width = 24, height = 24 }: CloudXLogoProps) {
  return (
    <img
      src="/cloud-x-logo.png"
      alt="Cloud-X Logo"
      className={className}
      width={width}
      height={height}
    />
  )
}
