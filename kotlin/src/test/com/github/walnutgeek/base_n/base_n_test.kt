package com.github.walnutgeek.base_n

import org.junit.Test
import java.io.File
import java.lang.IndexOutOfBoundsException
import java.util.*
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertSame

data class EncodesKey(val testName:String, val base:Int)

const val BENCH_DIR = "../benchmark"

class Samples(val bins:Map<String,ByteArray>,
              val encodesWithCheck:Map<EncodesKey,String>,
              val encodes:Map<EncodesKey,String>)

val SAMPLES:Samples by lazy {
    val dir = File("$BENCH_DIR/samples")
    val binPairs = mutableListOf<Pair<String,ByteArray>>()
    val ewcPairs = mutableListOf<Pair<EncodesKey,String>>()
    val ePairs = mutableListOf<Pair<EncodesKey,String>>()
    for(f in dir.listFiles()!!) {
        if ( f.isFile ){
            val testName = f.nameWithoutExtension
            val ext = f.extension
            fun ek(offset:Int):EncodesKey = EncodesKey(testName, ext.substring(offset).toInt())
            when {
                ext == "bin" -> binPairs.add( testName to f.readBytes())
                ext.startsWith("ewc") -> ewcPairs.add(ek(3) to f.readText())
                ext.startsWith("e") -> ePairs.add(ek(1) to f.readText())
            }
        }
    }
    Samples(
        mapOf(*binPairs.toTypedArray()),
        mapOf(*ewcPairs.toTypedArray()),
        mapOf(*ePairs.toTypedArray()))
}

fun intArray(vararg a:Int):IntArray = a

class BaseNTest {

    @Test
    fun testAlphabet() {
        val alphabet = Alphabet.fromString("abc")
        val alphabet2 = Alphabet.fromString("abc")
        assertSame(alphabet, alphabet2)
        assertEquals("abc", alphabet.key)
        assertEquals(3, alphabet.decoder.fromBase)
        assertEquals(256, alphabet.decoder.toBase)
        assertEquals(55451, alphabet.encoder.fromLog)
        assertEquals(10986, alphabet.encoder.toLog)
        assertEquals(1, alphabet.inverse['b'])
        assertEquals(null, alphabet.inverse['q'])
        assertEquals(0, Arrays.compare(intArray(1, 2, 0), alphabet.toDigits("bca")))
        assertEquals("bca", alphabet.toChars(intArray(1, 2, 0)))
        assertFailsWith<IndexOutOfBoundsException> {
            alphabet.toDigits("bcx")
        }
        assertFailsWith<IndexOutOfBoundsException> {
            alphabet.toChars(intArray(1,2,3))
        }

    }

    @Test
    fun testCodecs() {
        assertEquals(40, SAMPLES.bins.size)
        runThruSamples { id -> BigIntBaseN(Alphabet.predefined(id)) }
        runThruSamples { id -> LoopBaseN(Alphabet.predefined(id)) }
    }

    private fun runThruSamples(factory: (id:Int)->BaseN) {
        val codecs:Map<Int,BaseN> = mapOf(* ALPHABETS.keys.map { it to factory(it)}.toTypedArray())
        SAMPLES.encodes.forEach { (ek, v) ->
            val bytes = SAMPLES.bins[ek.testName]!!
            val c = codecs[ek.base]!!
            val encode = c.encode(bytes)
            assertEquals(encode, v)
            assertEquals(0, Arrays.compare(c.decode(encode), bytes))
        }
        SAMPLES.encodesWithCheck.forEach { (ek, v) ->
            val bytes = SAMPLES.bins[ek.testName]!!
            val c = codecs[ek.base]!!
            val encode = c.encodeCheck(bytes)
            assertEquals(encode, v)
            assertEquals(0, Arrays.compare(c.decodeCheck(encode), bytes))
        }
    }

}


