import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'

interface GalacticSpaceProps {
  onCameraPositionChange?: (position: THREE.Vector3) => void
}

export function GalacticSpace({ onCameraPositionChange }: GalacticSpaceProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const starsRef = useRef<THREE.Points | null>(null)
  const axesHelperRef = useRef<THREE.AxesHelper | null>(null)
  const animationFrameRef = useRef<number | null>(null)

  // Camera control state
  const [cameraPosition, setCameraPosition] = useState({ x: 0, y: 0, z: 50 })
  const [cameraRotation, setCameraRotation] = useState({ x: 0, y: 0 })
  const isDragging = useRef(false)
  const previousMousePosition = useRef({ x: 0, y: 0 })

  // Initialize Three.js scene
  useEffect(() => {
    if (!containerRef.current) return

    // Scene setup
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x000510)
    sceneRef.current = scene

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      2000
    )
    camera.position.set(cameraPosition.x, cameraPosition.y, cameraPosition.z)
    cameraRef.current = camera

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    containerRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Add coordinate axes helper (X=red, Y=green, Z=blue)
    const axesHelper = new THREE.AxesHelper(100)
    scene.add(axesHelper)
    axesHelperRef.current = axesHelper

    // Create starfield
    const starGeometry = new THREE.BufferGeometry()
    const starCount = 15000
    const positions = new Float32Array(starCount * 3)
    const colors = new Float32Array(starCount * 3)

    for (let i = 0; i < starCount * 3; i += 3) {
      // Spread stars in a large sphere
      const radius = Math.random() * 1500 + 500
      const theta = Math.random() * Math.PI * 2
      const phi = Math.random() * Math.PI

      positions[i] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i + 2] = radius * Math.cos(phi)

      // Varied star colors (white, blue-white, yellow-white)
      const colorVariation = Math.random()
      if (colorVariation < 0.7) {
        // White stars
        colors[i] = 1
        colors[i + 1] = 1
        colors[i + 2] = 1
      } else if (colorVariation < 0.85) {
        // Blue-white stars
        colors[i] = 0.8
        colors[i + 1] = 0.9
        colors[i + 2] = 1
      } else {
        // Yellow-white stars
        colors[i] = 1
        colors[i + 1] = 0.95
        colors[i + 2] = 0.8
      }
    }

    starGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    starGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    const starMaterial = new THREE.PointsMaterial({
      size: 2,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      sizeAttenuation: true
    })

    const stars = new THREE.Points(starGeometry, starMaterial)
    scene.add(stars)
    starsRef.current = stars

    // Add ambient light
    const ambientLight = new THREE.AmbientLight(0x404060, 0.5)
    scene.add(ambientLight)

    // Add directional light
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1)
    directionalLight.position.set(100, 100, 100)
    scene.add(directionalLight)

    // Animation loop
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate)

      // Slight rotation of starfield for ambient motion
      if (starsRef.current) {
        starsRef.current.rotation.y += 0.0001
      }

      renderer.render(scene, camera)
    }
    animate()

    // Handle window resize
    const handleResize = () => {
      if (!containerRef.current || !cameraRef.current || !rendererRef.current) return

      const width = containerRef.current.clientWidth
      const height = containerRef.current.clientHeight

      cameraRef.current.aspect = width / height
      cameraRef.current.updateProjectionMatrix()
      rendererRef.current.setSize(width, height)
    }
    window.addEventListener('resize', handleResize)

    // Mouse drag for orbital motion
    const handleMouseDown = (e: MouseEvent) => {
      isDragging.current = true
      previousMousePosition.current = { x: e.clientX, y: e.clientY }
    }

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return

      const deltaX = e.clientX - previousMousePosition.current.x
      const deltaY = e.clientY - previousMousePosition.current.y

      setCameraRotation(prev => ({
        x: prev.x + deltaY * 0.005,
        y: prev.y + deltaX * 0.005
      }))

      previousMousePosition.current = { x: e.clientX, y: e.clientY }
    }

    const handleMouseUp = () => {
      isDragging.current = false
    }

    renderer.domElement.addEventListener('mousedown', handleMouseDown)
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      renderer.domElement.removeEventListener('mousedown', handleMouseDown)
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement)
      }
      renderer.dispose()
    }
  }, [])

  // Update camera position and rotation
  useEffect(() => {
    if (!cameraRef.current) return

    const camera = cameraRef.current

    // Apply rotation (orbital motion)
    const distance = Math.sqrt(
      cameraPosition.x ** 2 +
      cameraPosition.y ** 2 +
      cameraPosition.z ** 2
    )

    camera.position.x = cameraPosition.x + Math.sin(cameraRotation.y) * distance * 0.1
    camera.position.y = cameraPosition.y + Math.sin(cameraRotation.x) * distance * 0.1
    camera.position.z = cameraPosition.z + Math.cos(cameraRotation.y) * distance * 0.1

    camera.lookAt(0, 0, 0)

    if (onCameraPositionChange) {
      onCameraPositionChange(camera.position)
    }
  }, [cameraPosition, cameraRotation, onCameraPositionChange])

  // Navigation controls
  const moveCamera = (direction: 'up' | 'down' | 'left' | 'right') => {
    const moveAmount = 5

    setCameraPosition(prev => {
      switch (direction) {
        case 'up':
          return { ...prev, y: prev.y + moveAmount }
        case 'down':
          return { ...prev, y: prev.y - moveAmount }
        case 'left':
          return { ...prev, x: prev.x - moveAmount }
        case 'right':
          return { ...prev, x: prev.x + moveAmount }
        default:
          return prev
      }
    })
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Navigation Controls */}
      <div
        style={{
          position: 'absolute',
          bottom: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '10px'
        }}
      >
        {/* Up button */}
        <button
          onClick={() => moveCamera('up')}
          style={{
            width: '50px',
            height: '50px',
            background: 'rgba(20, 30, 60, 0.8)',
            border: '2px solid rgba(100, 150, 255, 0.6)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '20px',
            cursor: 'pointer',
            backdropFilter: 'blur(10px)',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(30, 50, 100, 0.9)'
            e.currentTarget.style.borderColor = 'rgba(120, 180, 255, 0.9)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(20, 30, 60, 0.8)'
            e.currentTarget.style.borderColor = 'rgba(100, 150, 255, 0.6)'
          }}
        >
          ▲
        </button>

        {/* Left, Center, Right buttons */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => moveCamera('left')}
            style={{
              width: '50px',
              height: '50px',
              background: 'rgba(20, 30, 60, 0.8)',
              border: '2px solid rgba(100, 150, 255, 0.6)',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '20px',
              cursor: 'pointer',
              backdropFilter: 'blur(10px)',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(30, 50, 100, 0.9)'
              e.currentTarget.style.borderColor = 'rgba(120, 180, 255, 0.9)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(20, 30, 60, 0.8)'
              e.currentTarget.style.borderColor = 'rgba(100, 150, 255, 0.6)'
            }}
          >
            ◄
          </button>

          {/* Center info display */}
          <div
            style={{
              width: '50px',
              height: '50px',
              background: 'rgba(20, 30, 60, 0.6)',
              border: '2px solid rgba(100, 150, 255, 0.4)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'rgba(150, 200, 255, 0.8)',
              fontSize: '10px',
              backdropFilter: 'blur(10px)'
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div>X: {cameraPosition.x.toFixed(0)}</div>
              <div>Y: {cameraPosition.y.toFixed(0)}</div>
              <div>Z: {cameraPosition.z.toFixed(0)}</div>
            </div>
          </div>

          <button
            onClick={() => moveCamera('right')}
            style={{
              width: '50px',
              height: '50px',
              background: 'rgba(20, 30, 60, 0.8)',
              border: '2px solid rgba(100, 150, 255, 0.6)',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '20px',
              cursor: 'pointer',
              backdropFilter: 'blur(10px)',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(30, 50, 100, 0.9)'
              e.currentTarget.style.borderColor = 'rgba(120, 180, 255, 0.9)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(20, 30, 60, 0.8)'
              e.currentTarget.style.borderColor = 'rgba(100, 150, 255, 0.6)'
            }}
          >
            ►
          </button>
        </div>

        {/* Down button */}
        <button
          onClick={() => moveCamera('down')}
          style={{
            width: '50px',
            height: '50px',
            background: 'rgba(20, 30, 60, 0.8)',
            border: '2px solid rgba(100, 150, 255, 0.6)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '20px',
            cursor: 'pointer',
            backdropFilter: 'blur(10px)',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(30, 50, 100, 0.9)'
            e.currentTarget.style.borderColor = 'rgba(120, 180, 255, 0.9)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(20, 30, 60, 0.8)'
            e.currentTarget.style.borderColor = 'rgba(100, 150, 255, 0.6)'
          }}
        >
          ▼
        </button>
      </div>

      {/* Instructions overlay */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          background: 'rgba(20, 30, 60, 0.8)',
          border: '2px solid rgba(100, 150, 255, 0.6)',
          borderRadius: '8px',
          padding: '15px',
          color: 'rgba(200, 220, 255, 0.9)',
          fontSize: '14px',
          backdropFilter: 'blur(10px)',
          fontFamily: 'monospace'
        }}
      >
        <div style={{ fontWeight: 'bold', marginBottom: '8px', color: 'rgba(120, 180, 255, 1)' }}>
          NAVIGATION CONTROLS
        </div>
        <div>• Drag to orbit</div>
        <div>• Use buttons to move</div>
        <div>• Axes: X(red) Y(green) Z(blue)</div>
      </div>
    </div>
  )
}
