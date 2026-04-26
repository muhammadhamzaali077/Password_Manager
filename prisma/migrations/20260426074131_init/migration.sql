-- CreateEnum
CREATE TYPE "Band" AS ENUM ('HEALTHY', 'OKAY', 'CRITICAL');

-- CreateTable
CREATE TABLE "Visitor" (
    "id" TEXT NOT NULL,
    "sessionToken" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "lastSeenAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Visitor_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ScoreSubmission" (
    "id" TEXT NOT NULL,
    "visitorId" TEXT NOT NULL,
    "passwordCount" INTEGER NOT NULL,
    "oldestPasswordAgeMonths" INTEGER NOT NULL,
    "score" INTEGER NOT NULL,
    "band" "Band" NOT NULL,
    "recommendations" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ScoreSubmission_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Visitor_sessionToken_key" ON "Visitor"("sessionToken");

-- CreateIndex
CREATE INDEX "ScoreSubmission_visitorId_createdAt_idx" ON "ScoreSubmission"("visitorId", "createdAt" DESC);

-- AddForeignKey
ALTER TABLE "ScoreSubmission" ADD CONSTRAINT "ScoreSubmission_visitorId_fkey" FOREIGN KEY ("visitorId") REFERENCES "Visitor"("id") ON DELETE CASCADE ON UPDATE CASCADE;
