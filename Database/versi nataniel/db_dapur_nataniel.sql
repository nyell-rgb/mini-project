-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: db_dapur
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ingredients`
--

DROP TABLE IF EXISTS `ingredients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ingredients` (
  `id_ingredient` int(11) NOT NULL AUTO_INCREMENT,
  `nama_bahan` varchar(100) NOT NULL,
  `kategori_bahan` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_ingredient`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ingredients`
--

LOCK TABLES `ingredients` WRITE;
/*!40000 ALTER TABLE `ingredients` DISABLE KEYS */;
INSERT INTO `ingredients` VALUES (1,'Nasi Putih','Karbohidrat'),(2,'Telur Ayam','Protein'),(3,'Bawang Merah','Bumbu'),(4,'Bawang Putih','Bumbu'),(5,'Daun Bawang','Sayuran'),(6,'Minyak Goreng','Minyak/Lemak'),(7,'Margarin','Minyak/Lemak'),(8,'Garam','Bumbu'),(9,'Penyedap Rasa','Bumbu'),(10,'Kecap Manis','Bumbu'),(11,'Sawi Putih','Sayuran'),(12,'Cabai','Bumbu'),(13,'Daging Ayam','Protein'),(14,'Fillet Dada Ayam','Protein'),(15,'Daun Salam','Bumbu'),(16,'Lengkuas','Bumbu'),(17,'Saus Cabai','Bumbu'),(18,'Gula','Bumbu'),(19,'Bawang Bombay','Bumbu'),(20,'Saus Tiram','Bumbu'),(21,'Kecap Inggris','Bumbu'),(22,'Merica','Bumbu'),(23,'Cabai Hijau Besar','Bumbu'),(24,'Paprika','Sayuran');
/*!40000 ALTER TABLE `ingredients` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_favorites`
--

DROP TABLE IF EXISTS `recipe_favorites`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_favorites` (
  `id_recipe` int(11) NOT NULL,
  PRIMARY KEY (`id_recipe`),
  CONSTRAINT `recipe_favorites_ibfk_1` FOREIGN KEY (`id_recipe`) REFERENCES `recipes` (`id_recipe`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_favorites`
--

LOCK TABLES `recipe_favorites` WRITE;
/*!40000 ALTER TABLE `recipe_favorites` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_favorites` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_ingredients`
--

DROP TABLE IF EXISTS `recipe_ingredients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_ingredients` (
  `id_recipe` int(11) NOT NULL,
  `id_ingredient` int(11) NOT NULL,
  `jumlah_kebutuhan` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_recipe`,`id_ingredient`),
  KEY `id_ingredient` (`id_ingredient`),
  CONSTRAINT `recipe_ingredients_ibfk_1` FOREIGN KEY (`id_recipe`) REFERENCES `recipes` (`id_recipe`) ON DELETE CASCADE,
  CONSTRAINT `recipe_ingredients_ibfk_2` FOREIGN KEY (`id_ingredient`) REFERENCES `ingredients` (`id_ingredient`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_ingredients`
--

LOCK TABLES `recipe_ingredients` WRITE;
/*!40000 ALTER TABLE `recipe_ingredients` DISABLE KEYS */;
INSERT INTO `recipe_ingredients` VALUES (1,1,'1 piring'),(1,2,'1-2 butir'),(1,3,'4 siung'),(1,4,'2 siung'),(1,5,'1 batang'),(1,7,'2 sdm'),(1,8,'1/2 sdt'),(1,9,'1/4 sdt'),(1,10,'1 sdm'),(2,3,'2 siung'),(2,4,'1 siung'),(2,9,'Secukupnya'),(2,11,'1 bonggol'),(2,12,'3 buah'),(3,3,'3 siung'),(3,4,'2 siung'),(3,8,'Secukupnya'),(3,9,'Secukupnya'),(3,10,'3 sdm'),(3,13,'250 gram'),(3,15,'1 lembar'),(3,16,'1 ruas'),(3,17,'1 sdm'),(3,18,'Secukupnya'),(4,4,'2 siung'),(4,7,'2 sdm'),(4,8,'Secukupnya'),(4,10,'2 sdm'),(4,13,'250 gram'),(4,19,'1/2 buah'),(4,20,'1 sdm'),(4,21,'1 sdm'),(4,22,'Secukupnya'),(5,3,'3 siung'),(5,4,'2 siung'),(5,8,'Secukupnya'),(5,14,'250 gram'),(5,20,'1 sdm'),(5,22,'Secukupnya'),(5,23,'3 buah'),(5,24,'1/2 buah');
/*!40000 ALTER TABLE `recipe_ingredients` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipes`
--

DROP TABLE IF EXISTS `recipes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipes` (
  `id_recipe` int(11) NOT NULL AUTO_INCREMENT,
  `nama_resep` varchar(150) NOT NULL,
  `waktu_masak` int(11) DEFAULT NULL,
  `langkah_pembuatan` text DEFAULT NULL,
  `foto` varchar(255) DEFAULT NULL,
  `favorit` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id_recipe`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipes`
--

LOCK TABLES `recipes` WRITE;
/*!40000 ALTER TABLE `recipes` DISABLE KEYS */;
INSERT INTO `recipes` VALUES (1,'Nasi Goreng Telur',15,'1. Panaskan minyak/margarin di wajan api sedang. Tumis irisan bawang merah & putih sampai harum.\n2. Geser bumbu ke pinggir wajan, pecahkan telur di sisi kosong lalu orak-arik sampai matang.\n3. Masukkan nasi putih, aduk rata dengan tumisan bawang dan telur.\n4. Tambahkan garam, penyedap rasa, dan kecap manis. Aduk terus dengan api agak besar hingga bumbu merata & smoky.\n5. Masukkan irisan daun bawang, aduk sebentar hingga agak layu, lalu matikan kompor.\n6. Angkat dan sajikan hangat.',NULL,1),(2,'Tumis Sawi Putih',10,'1. Tumis bawang merah, bawang putih, dan cabai sampai harum.\n2. Masukkan potongan sawi putih, beri sedikit air, garam, dan penyedap.\n3. Tumis sebentar hingga sawi layu, lalu sajikan.',NULL,1),(3,'Ayam Kecap Teflon (Tanpa Ungkep)',20,'1. Tumis bawang merah, bawang putih, daun salam, dan lengkuas sampai harum.\n2. Masukkan potongan ayam, aduk sampai warnanya berubah pucat.\n3. Tuangkan air secukupnya, bumbui dengan kecap manis, saus cabai, garam, gula, dan kaldu bubuk.\n4. Tutup wajan sebentar agar ayam matang merata. Masak hingga air menyusut, berminyak, dan bumbu meresap.',NULL,1),(4,'Ayam Goreng Mentega',20,'1. Bumbui ayam dengan sedikit garam dan merica, lalu goreng sebentar hingga berkulit (jangan terlalu kering). Sisihkan.\n2. Lelehkan margarin di wajan, tumis bawang putih dan bawang bombay sampai harum dan layu.\n3. Masukkan ayam goreng, tambahkan kecap manis, saus tiram, dan kecap inggris.\n4. Aduk rata, beri sedikit air, lalu masak dengan api kecil sampai bumbu meresap dan kuah mengental.',NULL,1),(5,'Ayam Tumis Cabai Ijo / Paprika',15,'1. Panaskan sedikit minyak, tumis bawang merah, bawang putih, dan cabai hijau hingga harum.\n2. Masukkan potongan ayam fillet, aduk sampai ayam berubah warna dan kaku.\n3. Masukkan paprika (jika pakai) dan bumbui dengan saus tiram, garam, serta merica.\n4. Aduk cepat dengan api besar selama 2-3 menit hingga bumbu meresap dan ayam matang.',NULL,0);
/*!40000 ALTER TABLE `recipes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id_users` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('Chef','Ibu Rumah Tangga','Anak Kos','pembaca','pemula') NOT NULL DEFAULT 'pemula',
  PRIMARY KEY (`id_users`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-21 13:16:35
