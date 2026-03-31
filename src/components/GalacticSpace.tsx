import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import './GalacticSpace.css'

interface GalacticSpaceProps {
  onCameraPositionChange?: (position: THREE.Vector3) => void
}

type NavAction = 'up' | 'down' | 'left' | 'right' | 'orbitLeft' | 'orbitRight' | 'zoomIn' | 'zoomOut'

const ORIGIN = new THREE.Vector3(0, 0, 0)

function createLabelSprite(text: string, color: string) {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 96

  const context = canvas.getContext('2d')
  if (!context) return null

  context.fillStyle = 'rgba(0, 8, 30, 0.82)'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.strokeStyle = color
  context.lineWidth = 4
  context.strokeRect(4, 4, canvas.width - 8, canvas.height - 8)
  context.font = 'bold 42px Courier New'
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillStyle = color
  context.fillText(text, canvas.width / 2, canvas.height / 2)

  const texture = new THREE.CanvasTexture(canvas)
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(34, 12, 1)

  return { sprite, texture, material }
}

export function GalacticSpace({ onCameraPositionChange }: GalacticSpaceProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const autoOrbitRef = useRef(true)
  const orbitRef = useRef({ radius: 170, theta: Math.PI / 4, phi: Math.PI / 2.25 })
  const activeActionRef = useRef<NavAction | null>(null)
  const lastReadoutUpdateRef = useRef(0)
  const wavePhaseRef = useRef(0)

  // Camera control state
  const [cameraReadout, setCameraReadout] = useState({ x: 0, y: 0, z: 0 })
  const isDragging = useRef(false)
  const previousMousePosition = useRef({ x: 0, y: 0 })

  const clampPhi = (value: number) => Math.max(0.2, Math.min(Math.PI - 0.2, value))

  const updateCameraFromOrbit = () => {
    if (!cameraRef.current) return

    const { radius, theta, phi } = orbitRef.current
    const camera = cameraRef.current

    camera.position.x = radius * Math.sin(phi) * Math.cos(theta)
    camera.position.y = radius * Math.cos(phi)
    camera.position.z = radius * Math.sin(phi) * Math.sin(theta)
    camera.lookAt(ORIGIN)
  }

  const syncCameraReadout = () => {
    if (!cameraRef.current) return

    const { x, y, z } = cameraRef.current.position
    setCameraReadout({ x, y, z })

    if (onCameraPositionChange) {
      onCameraPositionChange(cameraRef.current.position)
    }
  }

  const applyNavAction = (action: NavAction, intensity = 1) => {
    const orbitStep = 0.085 * intensity
    const tiltStep = 0.07 * intensity
    const zoomStep = 7 * intensity

    switch (action) {
      case 'up':
        orbitRef.current.phi = clampPhi(orbitRef.current.phi - tiltStep)
        break
      case 'down':
        orbitRef.current.phi = clampPhi(orbitRef.current.phi + tiltStep)
        break
      case 'left':
        orbitRef.current.theta -= orbitStep
        break
      case 'right':
        orbitRef.current.theta += orbitStep
        break
      case 'orbitLeft':
        orbitRef.current.theta -= orbitStep * 1.75
        break
      case 'orbitRight':
        orbitRef.current.theta += orbitStep * 1.75
        break
      case 'zoomIn':
        orbitRef.current.radius = Math.max(40, orbitRef.current.radius - zoomStep)
        break
      case 'zoomOut':
        orbitRef.current.radius = Math.min(380, orbitRef.current.radius + zoomStep)
        break
      default:
        break
    }

    updateCameraFromOrbit()
    syncCameraReadout()
  }

  // Initialize Three.js scene
  useEffect(() => {
    if (!containerRef.current) return

    const clock = new THREE.Clock()
    const geometriesToDispose: THREE.BufferGeometry[] = []
    const materialsToDispose: THREE.Material[] = []
    const texturesToDispose: THREE.Texture[] = []

    // Scene setup
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x000510)

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      2000
    )
    cameraRef.current = camera
    updateCameraFromOrbit()

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    containerRef.current.appendChild(renderer.domElement)

    // Add coordinate axes helper (X=red, Y=green, Z=blue)
    const axesHelper = new THREE.AxesHelper(220)
    scene.add(axesHelper)

    // Make coordinates easier to read with bright axis arrows and a reference grid.
    const coordinateGroup = new THREE.Group()
    const arrowLength = 180
    const headLength = 14
    const headWidth = 8
    coordinateGroup.add(new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, 0), arrowLength, 0xff4d4d, headLength, headWidth))
    coordinateGroup.add(new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), arrowLength, 0x4dff88, headLength, headWidth))
    coordinateGroup.add(new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 0), arrowLength, 0x4da6ff, headLength, headWidth))
    scene.add(coordinateGroup)

    const gridHelper = new THREE.GridHelper(500, 25, 0x2f64ff, 0x1b2d55)
    scene.add(gridHelper)
    gridHelper.position.y = -0.01

    const cubeSize = 70
    const cubeGeometry = new THREE.BoxGeometry(cubeSize, cubeSize, cubeSize)
    const cubeEdges = new THREE.EdgesGeometry(cubeGeometry)
    const cubeMaterial = new THREE.LineBasicMaterial({ color: 0xffd166 })
    const cubeReference = new THREE.LineSegments(cubeEdges, cubeMaterial)
    cubeReference.position.set(cubeSize / 2, cubeSize / 2, cubeSize / 2)
    scene.add(cubeReference)
    geometriesToDispose.push(cubeGeometry, cubeEdges)
    materialsToDispose.push(cubeMaterial)

    const inputGeometry = new THREE.PlaneGeometry(40, 22)
    const inputMaterial = new THREE.MeshStandardMaterial({
      color: 0xff8a66,
      emissive: 0x6e2b1f,
      emissiveIntensity: 0.55,
      side: THREE.DoubleSide
    })
    const inputRect = new THREE.Mesh(inputGeometry, inputMaterial)
    inputRect.position.set(-145, 20, 0)
    inputRect.rotation.y = Math.PI / 2
    scene.add(inputRect)

    const outputGeometry = new THREE.PlaneGeometry(44, 22)
    const outputMaterial = new THREE.MeshStandardMaterial({
      color: 0x66d3ff,
      emissive: 0x1d4561,
      emissiveIntensity: 0.55,
      side: THREE.DoubleSide
    })
    const outputRect = new THREE.Mesh(outputGeometry, outputMaterial)
    outputRect.position.set(0, -152, 0)
    outputRect.rotation.x = -Math.PI / 2
    scene.add(outputRect)

    geometriesToDispose.push(inputGeometry, outputGeometry)
    materialsToDispose.push(inputMaterial, outputMaterial)

    const inputLabel = createLabelSprite('INPUT', '#ffcbb7')
    const outputLabel = createLabelSprite('OUTPUT', '#bde6ff')
    if (inputLabel) {
      inputLabel.sprite.position.set(-145, 42, 0)
      scene.add(inputLabel.sprite)
      materialsToDispose.push(inputLabel.material)
      texturesToDispose.push(inputLabel.texture)
    }
    if (outputLabel) {
      outputLabel.sprite.position.set(0, -128, 0)
      scene.add(outputLabel.sprite)
      materialsToDispose.push(outputLabel.material)
      texturesToDispose.push(outputLabel.texture)
    }

    const wavePointCount = 120
    const wave1Positions = new Float32Array(wavePointCount * 3)
    const wave2Positions = new Float32Array(wavePointCount * 3)

    const wave1Geometry = new THREE.BufferGeometry()
    wave1Geometry.setAttribute('position', new THREE.BufferAttribute(wave1Positions, 3))
    const wave1Material = new THREE.LineBasicMaterial({ color: 0xffb98f })
    const wave1 = new THREE.Line(wave1Geometry, wave1Material)
    wave1.frustumCulled = false
    scene.add(wave1)

    const wave2Geometry = new THREE.BufferGeometry()
    wave2Geometry.setAttribute('position', new THREE.BufferAttribute(wave2Positions, 3))
    const wave2Material = new THREE.LineBasicMaterial({ color: 0x86d6ff })
    const wave2 = new THREE.Line(wave2Geometry, wave2Material)
    wave2.frustumCulled = false
    scene.add(wave2)

    geometriesToDispose.push(wave1Geometry, wave2Geometry)
    materialsToDispose.push(wave1Material, wave2Material)

    // Create starfield
    const starGeometry = new THREE.BufferGeometry()
    const starCount = 3500
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

    geometriesToDispose.push(starGeometry)
    materialsToDispose.push(starMaterial)

    // Add ambient light
    const ambientLight = new THREE.AmbientLight(0x404060, 0.72)
    scene.add(ambientLight)

    // Add directional light
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2)
    directionalLight.position.set(110, 140, 100)
    scene.add(directionalLight)

    const fillLight = new THREE.DirectionalLight(0x79b8ff, 0.5)
    fillLight.position.set(-140, -40, 80)
    scene.add(fillLight)

    const updateWaves = () => {
      const phase = wavePhaseRef.current
      const frequency = Math.PI * 7
      const inputPoint = inputRect.position
      const outputPoint = outputRect.position

      for (let i = 0; i < wavePointCount; i += 1) {
        const t = i / (wavePointCount - 1)

        const x1 = THREE.MathUtils.lerp(inputPoint.x, 0, t)
        const y1 = THREE.MathUtils.lerp(inputPoint.y, 0, t)
        const z1 = THREE.MathUtils.lerp(inputPoint.z, 0, t)
        wave1Positions[i * 3] = x1
        wave1Positions[i * 3 + 1] = y1 + Math.sin(t * frequency + phase) * 5.5
        wave1Positions[i * 3 + 2] = z1 + Math.cos(t * frequency + phase * 1.1) * 3.2

        const x2 = THREE.MathUtils.lerp(0, outputPoint.x, t)
        const y2 = THREE.MathUtils.lerp(0, outputPoint.y, t)
        const z2 = THREE.MathUtils.lerp(0, outputPoint.z, t)
        wave2Positions[i * 3] = x2 + Math.sin(t * frequency + phase * 1.25) * 5.2
        wave2Positions[i * 3 + 1] = y2
        wave2Positions[i * 3 + 2] = z2 + Math.cos(t * frequency + phase * 0.95) * 3
      }

      const wave1Attribute = wave1Geometry.attributes.position as THREE.BufferAttribute
      const wave2Attribute = wave2Geometry.attributes.position as THREE.BufferAttribute
      wave1Attribute.needsUpdate = true
      wave2Attribute.needsUpdate = true
    }

    // Animation loop
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate)
      const delta = clock.getDelta()

      if (activeActionRef.current) {
        applyNavAction(activeActionRef.current, 1.1)
      }

      if (autoOrbitRef.current && !isDragging.current && !activeActionRef.current) {
        orbitRef.current.theta += delta * 0.5
        updateCameraFromOrbit()
      }

      stars.rotation.y += delta * 0.18
      wavePhaseRef.current += delta * 4.5
      updateWaves()
      wave1Geometry.computeBoundingSphere()
      wave2Geometry.computeBoundingSphere()

      if (inputLabel) {
        inputLabel.sprite.quaternion.copy(camera.quaternion)
      }
      if (outputLabel) {
        outputLabel.sprite.quaternion.copy(camera.quaternion)
      }

      const now = performance.now()
      if (now - lastReadoutUpdateRef.current > 120) {
        syncCameraReadout()
        lastReadoutUpdateRef.current = now
      }

      renderer.render(scene, camera)
    }
    animate()

    // Handle window resize
    const handleResize = () => {
      if (!containerRef.current || !cameraRef.current) return

      const width = containerRef.current.clientWidth
      const height = containerRef.current.clientHeight

      cameraRef.current.aspect = width / height
      cameraRef.current.updateProjectionMatrix()
      renderer.setSize(width, height)
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

      orbitRef.current.theta += deltaX * 0.014
      orbitRef.current.phi = clampPhi(orbitRef.current.phi - deltaY * 0.01)
      updateCameraFromOrbit()
      syncCameraReadout()

      previousMousePosition.current = { x: e.clientX, y: e.clientY }
    }

    const handleMouseUp = () => {
      isDragging.current = false
    }

    renderer.domElement.addEventListener('mousedown', handleMouseDown)
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    window.addEventListener('mouseleave', handleMouseUp)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      renderer.domElement.removeEventListener('mousedown', handleMouseDown)
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
      window.removeEventListener('mouseleave', handleMouseUp)

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement)
      }
      for (const geometry of geometriesToDispose) {
        geometry.dispose()
      }
      for (const material of materialsToDispose) {
        material.dispose()
      }
      for (const texture of texturesToDispose) {
        texture.dispose()
      }
      renderer.dispose()
    }
  }, [])

  // Navigation controls
  const triggerAction = (action: NavAction) => {
    applyNavAction(action)
  }

  const startAction = (action: NavAction) => {
    activeActionRef.current = action
  }

  const stopAction = () => {
    activeActionRef.current = null
  }

  return (
    <div className="galactic-space">
      <div ref={containerRef} className="galactic-canvas" />

      {/* Navigation Controls */}
      <div className="nav-controls">
        {/* Up button */}
        <button
          onMouseDown={() => startAction('up')}
          onMouseUp={stopAction}
          onMouseLeave={stopAction}
          onTouchStart={() => startAction('up')}
          onTouchEnd={stopAction}
          onClick={() => triggerAction('up')}
          className="nav-btn"
        >
          ▲
        </button>

        {/* Left, Center, Right buttons */}
        <div className="nav-row">
          <button
            onMouseDown={() => startAction('left')}
            onMouseUp={stopAction}
            onMouseLeave={stopAction}
            onTouchStart={() => startAction('left')}
            onTouchEnd={stopAction}
            onClick={() => triggerAction('left')}
            className="nav-btn"
          >
            ◄
          </button>

          {/* Center info display */}
          <div className="nav-center">
            <div className="nav-center-text">
              <div>X: {cameraReadout.x.toFixed(0)}</div>
              <div>Y: {cameraReadout.y.toFixed(0)}</div>
              <div>Z: {cameraReadout.z.toFixed(0)}</div>
            </div>
          </div>

          <button
            onMouseDown={() => startAction('right')}
            onMouseUp={stopAction}
            onMouseLeave={stopAction}
            onTouchStart={() => startAction('right')}
            onTouchEnd={stopAction}
            onClick={() => triggerAction('right')}
            className="nav-btn"
          >
            ►
          </button>
        </div>

        {/* Down button */}
        <button
          onMouseDown={() => startAction('down')}
          onMouseUp={stopAction}
          onMouseLeave={stopAction}
          onTouchStart={() => startAction('down')}
          onTouchEnd={stopAction}
          onClick={() => triggerAction('down')}
          className="nav-btn"
        >
          ▼
        </button>

        <div className="nav-row nav-row-secondary">
          <button
            onMouseDown={() => startAction('orbitLeft')}
            onMouseUp={stopAction}
            onMouseLeave={stopAction}
            onTouchStart={() => startAction('orbitLeft')}
            onTouchEnd={stopAction}
            onClick={() => triggerAction('orbitLeft')}
            className="nav-btn nav-btn-orbit"
          >
            ⟲
          </button>

          <button
            onMouseDown={() => startAction('zoomIn')}
            onMouseUp={stopAction}
            onMouseLeave={stopAction}
            onTouchStart={() => startAction('zoomIn')}
            onTouchEnd={stopAction}
            onClick={() => triggerAction('zoomIn')}
            className="nav-btn"
          >
            +
          </button>

          <button
            onMouseDown={() => startAction('zoomOut')}
            onMouseUp={stopAction}
            onMouseLeave={stopAction}
            onTouchStart={() => startAction('zoomOut')}
            onTouchEnd={stopAction}
            onClick={() => triggerAction('zoomOut')}
            className="nav-btn"
          >
            −
          </button>

          <button
            onMouseDown={() => startAction('orbitRight')}
            onMouseUp={stopAction}
            onMouseLeave={stopAction}
            onTouchStart={() => startAction('orbitRight')}
            onTouchEnd={stopAction}
            onClick={() => triggerAction('orbitRight')}
            className="nav-btn nav-btn-orbit"
          >
            ⟳
          </button>
        </div>
      </div>

      {/* Instructions overlay */}
      <div className="instructions-overlay">
        <div className="instructions-title">
          NAVIGATION CONTROLS
        </div>
        <div>• Axis origin is fixed at screen center</div>
        <div>• Drag or arrows to orbit the camera</div>
        <div>• Auto-orbit runs continuously when idle</div>
        <div>• Orbit: ⟲ / ⟳ | Zoom: + / −</div>
        <div>• INPUT(-X) to origin and origin to OUTPUT(-Y)</div>
        <div>• Cube reference is in first octant</div>
      </div>
    </div>
  )
}
